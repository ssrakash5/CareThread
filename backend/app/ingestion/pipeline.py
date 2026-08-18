"""
End-to-end ingestion pipeline (spec section 5):
store -> extract -> normalize -> chunk -> embed -> extract facts/findings
-> search this patient's open threads -> propose thread / link evidence / no action.

Provider-agnostic: storage (S3/local), embeddings (Titan/local), extraction
(Claude/regex) and matching (Claude judge/rules) are all dispatched behind the
functions imported below according to ``settings.ai_provider`` / ``s3_bucket``.
"""
from datetime import date

from sqlalchemy.orm import Session

from app.models import Artifact, ArtifactChunk, Fact, Finding, CareThread, ProposedAction
from app.ingestion.extractors import chunk_text, extract_document, ExtractedFact
from app.ingestion.embeddings import embed_text
from app.ai.storage import store_raw, store_bytes
from app.agents.matching_agent import find_candidate_threads
from app.agents.action_agent import propose_thread as agent_propose_thread, propose_closure as agent_propose_closure


def _thread_type_for(finding_type: str) -> str:
    return "INCIDENTAL_PULMONARY_FOLLOWUP" if finding_type == "PULMONARY_NODULE" else "INCIDENTAL_FOLLOWUP"


def ingest_artifact(
    db: Session,
    patient_id: str,
    artifact_type: str,
    title: str,
    text: str,
    document_date: date,
    source_provider: str = "",
    auto_propose_threads: bool = True,
    raw_bytes: bytes | None = None,
    raw_ext: str = "",
    mime_type: str = "text/plain",
) -> dict:
    """``text`` drives chunking/extraction/matching regardless of source. If
    ``raw_bytes`` is given (e.g. an uploaded PDF or image), those bytes are
    stored as the artifact of record instead of ``text`` — ``text`` should
    then be the already-extracted document text (PDFs) or a human-written
    caption (images; per spec section 3, images are reference artifacts
    only and are never auto-interpreted)."""
    if raw_bytes is not None:
        s3_uri = store_bytes(patient_id, artifact_type, title, raw_bytes, raw_ext, mime_type)
    else:
        s3_uri = store_raw(patient_id, artifact_type, title, text)

    artifact = Artifact(
        patient_id=patient_id,
        artifact_type=artifact_type,
        source_provider=source_provider,
        document_date=document_date,
        s3_uri=s3_uri,
        mime_type=mime_type,
        title=title,
        status="PROCESSING",
    )
    db.add(artifact)
    db.flush()

    # --- chunk + embed ------------------------------------------------------
    extracted_chunks = chunk_text(text)
    chunk_rows, chunk_texts, chunk_embeddings = [], [], []
    for idx, ec in enumerate(extracted_chunks):
        embedding = embed_text(ec.text)
        chunk = ArtifactChunk(
            artifact_id=artifact.artifact_id,
            patient_id=patient_id,
            chunk_index=idx,
            chunk_text=ec.text,
            embedding=embedding,
            section_name=ec.section_name,
            page_number=ec.page_number,
        )
        db.add(chunk)
        chunk_rows.append(chunk)
        chunk_texts.append(ec.text)
        chunk_embeddings.append(embedding)
    db.flush()
    first_chunk_id = chunk_rows[0].chunk_id if chunk_rows else None

    # Images are reference artifacts only (spec section 3): the caption gets
    # chunked + embedded above for retrieval, but pixel content is never
    # auto-interpreted, so no fact/finding extraction or thread matching runs.
    if artifact_type == "IMAGE":
        artifact.status = "PROCESSED"
        return {
            "artifact_id": artifact.artifact_id,
            "chunks_created": len(chunk_rows),
            "facts_extracted": [],
            "findings_extracted": [],
            "proposed_actions": [],
            "match_candidates": [],
        }

    # --- extract facts + findings (Claude on Bedrock, or local regex) --------
    extraction = extract_document(text, artifact_type)
    facts = extraction.facts
    for i, f in enumerate(facts):
        chunk = chunk_rows[min(i, len(chunk_rows) - 1)] if chunk_rows else None
        db.add(Fact(
            patient_id=patient_id,
            artifact_id=artifact.artifact_id,
            chunk_id=chunk.chunk_id if chunk else None,
            fact_type=f.fact_type,
            fact_text=f.fact_text,
            normalized_value=f.normalized_value,
            confidence=f.confidence,
        ))

    artifact.status = "PROCESSED"

    result = {
        "artifact_id": artifact.artifact_id,
        "chunks_created": len(chunk_rows),
        "facts_extracted": [f.fact_type for f in facts],
        "findings_extracted": [
            {"finding_type": fd.finding_type, "anatomical_location": fd.anatomical_location,
             "description": fd.description, "followup_recommended": fd.followup_recommended,
             "followup_interval": fd.followup_interval}
            for fd in extraction.findings
        ],
        "proposed_actions": [],
        "match_candidates": [],
    }

    followup_fact = next((f for f in facts if f.fact_type == "FOLLOWUP_RECOMMENDATION"), None)
    completed_fact = next((f for f in facts if f.fact_type == "FOLLOWUP_COMPLETED"), None)

    # --- match against this patient's open threads --------------------------
    candidates = find_candidate_threads(
        db, patient_id, artifact, chunk_texts, chunk_embeddings,
        doc_location=extraction.anatomical_location,
        completed_hint=completed_fact is not None,
    )
    result["match_candidates"] = [
        {"thread_id": c.thread_id, "match_confidence": c.match_confidence,
         "reasons": c.reasons, "recommended_action": c.recommended_action,
         "relationship_type": c.relationship_type, "judged_by": c.judged_by}
        for c in candidates
    ]

    if candidates:
        top = candidates[0]
        link_action = ProposedAction(
            thread_id=top.thread_id,
            patient_id=patient_id,
            action_type="LINK_EVIDENCE",
            proposed_payload={"relationship_type": top.relationship_type},
            reason="; ".join(top.reasons),
            confidence=top.match_confidence,
            source_evidence={"artifact_id": artifact.artifact_id, "chunk_id": first_chunk_id},
        )
        db.add(link_action)
        db.flush()
        result["proposed_actions"].append({"action_id": link_action.action_id, "action_type": "LINK_EVIDENCE",
                                            "thread_id": top.thread_id, "status": link_action.status})

        if top.closes_obligation and top.match_confidence >= 0.75:
            closure_action = agent_propose_closure(
                db, top.thread_id, patient_id, artifact.artifact_id, first_chunk_id,
                reason="Follow-up imaging referenced in new evidence appears to complete the outstanding obligation.",
            )
            db.add(closure_action)
            db.flush()
            result["proposed_actions"].append({"action_id": closure_action.action_id, "action_type": "CLOSE_THREAD",
                                                "thread_id": top.thread_id, "status": closure_action.status})
        return result

    # --- no open thread matched: propose a new one for the primary finding ---
    if not auto_propose_threads:
        return result

    primary = next((fd for fd in extraction.findings if fd.followup_recommended), None)
    if primary is None or (followup_fact is None and not primary.followup_interval):
        return result

    location = primary.anatomical_location or extraction.anatomical_location
    finding = Finding(
        patient_id=patient_id,
        finding_type=primary.finding_type,
        anatomical_location=location,
        finding_description=primary.description,
        source_artifact_id=artifact.artifact_id,
        source_chunk_id=first_chunk_id,
    )
    db.add(finding)
    db.flush()

    pretty_type = primary.finding_type.replace("_", " ").title()
    pretty_loc = location.replace("_", " ").title() or "Unspecified Location"
    thread = CareThread(
        patient_id=patient_id,
        thread_type=_thread_type_for(primary.finding_type),
        title=f"Incidental {pretty_type} Follow-up ({pretty_loc})",
        finding_id=finding.finding_id,
        status="PROPOSED",
    )
    db.add(thread)
    db.flush()

    # action_agent derives the interval from followup_fact.normalized_value; if the
    # LLM only put the interval on the finding, synthesise a fact-like carrier.
    if followup_fact is None:
        followup_fact = ExtractedFact(
            fact_type="FOLLOWUP_RECOMMENDATION",
            fact_text=primary.description,
            normalized_value=primary.followup_interval.replace(" ", ""),
        )
    open_action = agent_propose_thread(db, patient_id, finding, followup_fact, artifact)
    open_action.thread_id = thread.thread_id
    db.add(open_action)
    db.flush()

    thread.due_at = date.fromisoformat(open_action.proposed_payload["due_at"])
    thread.priority = open_action.proposed_payload["priority"]

    result["proposed_actions"].append({"action_id": open_action.action_id, "action_type": "OPEN_THREAD",
                                        "thread_id": thread.thread_id, "status": open_action.status})
    result["thread_id"] = thread.thread_id
    return result
