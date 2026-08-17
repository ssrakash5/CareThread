"""
End-to-end ingestion pipeline (spec section 5):
store -> extract -> normalize -> chunk -> embed -> extract facts/findings
-> search this patient's open threads -> propose thread / link evidence / no action.
"""
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Artifact, ArtifactChunk, Fact, Finding, CareThread, ProposedAction
from app.ingestion.extractors import chunk_text, extract_facts, extract_anatomical_location
from app.ingestion.embeddings import embed_text
from app.agents.matching_agent import find_candidate_threads
from app.agents.action_agent import propose_thread as agent_propose_thread, propose_closure as agent_propose_closure


def _store_raw(patient_id: str, artifact_type: str, title: str, text: str) -> str:
    subdir = Path(settings.storage_dir) / patient_id / artifact_type.lower()
    subdir.mkdir(parents=True, exist_ok=True)
    safe_title = "".join(c if c.isalnum() or c in "-_." else "_" for c in title)
    path = subdir / f"{safe_title}.txt"
    path.write_text(text, encoding="utf-8")
    return f"local://{path.relative_to(Path(settings.storage_dir).parent)}"


def ingest_artifact(
    db: Session,
    patient_id: str,
    artifact_type: str,
    title: str,
    text: str,
    document_date: date,
    source_provider: str = "",
) -> dict:
    s3_uri = _store_raw(patient_id, artifact_type, title, text)

    artifact = Artifact(
        patient_id=patient_id,
        artifact_type=artifact_type,
        source_provider=source_provider,
        document_date=document_date,
        s3_uri=s3_uri,
        title=title,
        status="PROCESSING",
    )
    db.add(artifact)
    db.flush()

    extracted_chunks = chunk_text(text)
    chunk_rows = []
    chunk_texts = []
    chunk_embeddings = []
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

    facts = extract_facts(text)
    fact_rows = []
    for i, f in enumerate(facts):
        chunk = chunk_rows[min(i, len(chunk_rows) - 1)] if chunk_rows else None
        fact_row = Fact(
            patient_id=patient_id,
            artifact_id=artifact.artifact_id,
            chunk_id=chunk.chunk_id if chunk else None,
            fact_type=f.fact_type,
            fact_text=f.fact_text,
            normalized_value=f.normalized_value,
            confidence=f.confidence,
        )
        db.add(fact_row)
        fact_rows.append(fact_row)

    artifact.status = "PROCESSED"

    result = {
        "artifact_id": artifact.artifact_id,
        "chunks_created": len(chunk_rows),
        "facts_extracted": [f.fact_type for f in facts],
        "proposed_actions": [],
        "match_candidates": [],
    }

    nodule_fact = next((f for f in facts if f.fact_type == "PULMONARY_NODULE_FINDING"), None)
    followup_fact = next((f for f in facts if f.fact_type == "FOLLOWUP_RECOMMENDATION"), None)
    completed_fact = next((f for f in facts if f.fact_type == "FOLLOWUP_COMPLETED"), None)

    candidates = find_candidate_threads(db, patient_id, artifact, chunk_texts, chunk_embeddings)
    result["match_candidates"] = [
        {"thread_id": c.thread_id, "match_confidence": c.match_confidence,
         "reasons": c.reasons, "recommended_action": c.recommended_action}
        for c in candidates
    ]

    if candidates:
        top = candidates[0]
        rel_type = "COMPLETION_EVIDENCE" if completed_fact else "STATUS_UPDATE"
        link_action = ProposedAction(
            thread_id=top.thread_id,
            patient_id=patient_id,
            action_type="LINK_EVIDENCE",
            proposed_payload={"relationship_type": rel_type},
            reason="; ".join(top.reasons),
            confidence=top.match_confidence,
            source_evidence={"artifact_id": artifact.artifact_id,
                              "chunk_id": chunk_rows[0].chunk_id if chunk_rows else None},
        )
        db.add(link_action)
        db.flush()
        result["proposed_actions"].append({"action_id": link_action.action_id, "action_type": "LINK_EVIDENCE",
                                            "thread_id": top.thread_id, "status": link_action.status})

        if completed_fact and top.match_confidence >= 0.75:
            closure_action = agent_propose_closure(
                db, top.thread_id, patient_id, artifact.artifact_id,
                chunk_rows[0].chunk_id if chunk_rows else None,
                reason="Follow-up imaging referenced in new evidence appears to complete the outstanding obligation.",
            )
            db.add(closure_action)
            db.flush()
            result["proposed_actions"].append({"action_id": closure_action.action_id, "action_type": "CLOSE_THREAD",
                                                "thread_id": top.thread_id, "status": closure_action.status})

    elif nodule_fact and followup_fact:
        location = extract_anatomical_location(text)
        finding = Finding(
            patient_id=patient_id,
            finding_type="PULMONARY_NODULE",
            anatomical_location=location,
            finding_description=nodule_fact.fact_text,
            source_artifact_id=artifact.artifact_id,
            source_chunk_id=chunk_rows[0].chunk_id if chunk_rows else None,
        )
        db.add(finding)
        db.flush()

        thread = CareThread(
            patient_id=patient_id,
            thread_type="INCIDENTAL_PULMONARY_FOLLOWUP",
            title=f"Incidental Pulmonary Nodule Follow-up ({location.replace('_', ' ').title() or 'Unspecified Location'})",
            finding_id=finding.finding_id,
            status="PROPOSED",
        )
        db.add(thread)
        db.flush()

        open_action = agent_propose_thread(db, patient_id, finding, followup_fact, artifact)
        open_action.thread_id = thread.thread_id
        open_action.proposed_payload["due_at"] = open_action.proposed_payload["due_at"]
        db.add(open_action)
        db.flush()

        thread.due_at = date.fromisoformat(open_action.proposed_payload["due_at"])
        thread.priority = open_action.proposed_payload["priority"]

        result["proposed_actions"].append({"action_id": open_action.action_id, "action_type": "OPEN_THREAD",
                                            "thread_id": thread.thread_id, "status": open_action.status})
        result["thread_id"] = thread.thread_id

    return result
