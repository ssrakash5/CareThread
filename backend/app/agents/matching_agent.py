"""
Evidence matching agent (spec section 12). Deliberately not embeddings-only:
combines vector similarity with structured clinical signals so matches are
explainable to a clinician (spec section 13, Screen 3).

Two layers:
  1. ``_rule_candidates`` — deterministic scoring (same patient, anatomical
     location, finding type, title terms, chunk-embedding similarity). Always
     runs; it is the ``local`` provider and supplies hints to the judge.
  2. When ``settings.ai_provider == "bedrock"``, Claude judges every open
     thread for this patient (app/ai/matching.py) and its verdict wins. On
     any Bedrock error the rule verdicts are returned unchanged.

Patient-scoped only: never queries across patients.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import CareThread, Finding, ThreadEvidence, Artifact, ArtifactChunk
from app.ingestion.embeddings import cosine_similarity
from app.ingestion.extractors import extract_anatomical_location

log = logging.getLogger("carethread.matching")


@dataclass
class MatchCandidate:
    thread_id: str
    match_confidence: float
    reasons: List[str]
    recommended_action: str  # LINK_EVIDENCE | NEEDS_REVIEW | NO_MATCH
    relationship_type: str = "STATUS_UPDATE"  # COMPLETION_EVIDENCE | STATUS_UPDATE | NEW_INFORMATION
    closes_obligation: bool = False
    judged_by: str = "rules"  # "rules" | "bedrock"


OPEN_STATUSES = {"OPEN", "IN_PROGRESS", "AWAITING_EVIDENCE", "OVERDUE", "ESCALATED"}


def _open_threads(db: Session, patient_id: str) -> List[CareThread]:
    return db.execute(
        select(CareThread).where(
            CareThread.patient_id == patient_id,
            CareThread.status.in_(OPEN_STATUSES),
        )
    ).scalars().all()


def _rule_score(
    db: Session,
    thread: CareThread,
    finding: Optional[Finding],
    full_text: str,
    doc_location: str,
    chunk_embeddings: List[List[float]],
):
    """Return (score, reasons) for one thread. Pure heuristics."""
    reasons = ["same patient"]
    score = 0.35  # same-patient scoping already narrows the space substantially

    if finding and doc_location and finding.anatomical_location == doc_location:
        score += 0.25
        reasons.append(f"same anatomical location ({doc_location.replace('_', ' ').title()})")

    if finding and finding.finding_type.lower().replace("_", " ") in full_text.replace("_", " "):
        score += 0.15
        reasons.append("same finding type referenced")

    title_terms = [t for t in thread.title.lower().split() if len(t) > 4]
    title_hits = sum(1 for t in title_terms if t in full_text)
    if title_terms and title_hits / len(title_terms) > 0.4:
        score += 0.1
        reasons.append("terminology consistent with thread title")

    best_chunk_sim = 0.0
    prior_evidence = db.execute(
        select(ThreadEvidence).where(ThreadEvidence.thread_id == thread.thread_id)
    ).scalars().all()
    if prior_evidence and chunk_embeddings:
        prior_chunk_ids = [e.chunk_id for e in prior_evidence if e.chunk_id]
        if prior_chunk_ids:
            prior_chunks = db.execute(
                select(ArtifactChunk).where(ArtifactChunk.chunk_id.in_(prior_chunk_ids))
            ).scalars().all()
            for pc in prior_chunks:
                for emb in chunk_embeddings:
                    best_chunk_sim = max(best_chunk_sim, cosine_similarity(emb, pc.embedding))
    if best_chunk_sim > 0.3:
        score += min(best_chunk_sim, 0.6) * 0.2
        reasons.append(f"semantic similarity to existing thread evidence ({best_chunk_sim:.2f})")

    return min(score, 0.99), reasons


def _action_for(score: float) -> str:
    if score >= 0.75:
        return "LINK_EVIDENCE"
    if score >= 0.45:
        return "NEEDS_REVIEW"
    return "NO_MATCH"


def find_candidate_threads(
    db: Session,
    patient_id: str,
    artifact: Artifact,
    chunk_texts: List[str],
    chunk_embeddings: List[List[float]],
    doc_location: str = "",
    completed_hint: bool = False,
) -> List[MatchCandidate]:
    open_threads = _open_threads(db, patient_id)
    if not open_threads:
        return []

    full_text_raw = " ".join(chunk_texts)
    full_text = full_text_raw.lower()
    doc_location = doc_location or extract_anatomical_location(full_text)

    findings: Dict[str, Optional[Finding]] = {}
    rule_results: Dict[str, tuple] = {}
    for thread in open_threads:
        finding = db.get(Finding, thread.finding_id) if thread.finding_id else None
        findings[thread.thread_id] = finding
        rule_results[thread.thread_id] = _rule_score(db, thread, finding, full_text, doc_location, chunk_embeddings)

    candidates: List[MatchCandidate] = []

    if settings.ai_provider == "bedrock":
        try:
            from app.ai.matching import judge_matches_bedrock
            payload = []
            for thread in open_threads:
                f = findings[thread.thread_id]
                score, reasons = rule_results[thread.thread_id]
                payload.append({
                    "thread_id": thread.thread_id,
                    "title": thread.title,
                    "status": thread.status,
                    "finding_type": f.finding_type if f else "",
                    "anatomical_location": f.anatomical_location if f else "",
                    "finding_description": f.finding_description if f else "",
                    "due_at": thread.due_at.isoformat() if thread.due_at else "",
                    "rule_signals": reasons[1:] + [f"rule score {score:.2f}"],
                })
            judgments = {j["thread_id"]: j for j in judge_matches_bedrock(full_text_raw, artifact.artifact_type, payload)}
            for thread in open_threads:
                j = judgments.get(thread.thread_id)
                if not j or j["recommended_action"] == "NO_MATCH":
                    continue
                candidates.append(MatchCandidate(
                    thread_id=thread.thread_id,
                    match_confidence=round(j["match_confidence"], 2),
                    reasons=j["reasons"] or rule_results[thread.thread_id][1],
                    recommended_action=j["recommended_action"],
                    relationship_type=j["relationship_type"] if j["relationship_type"] != "UNRELATED" else "STATUS_UPDATE",
                    closes_obligation=bool(j.get("closes_obligation")),
                    judged_by="bedrock",
                ))
            candidates.sort(key=lambda c: c.match_confidence, reverse=True)
            return candidates
        except Exception as e:  # noqa: BLE001
            log.warning("Bedrock match judge failed (%s); using rule-based matching", e)
            candidates = []

    for thread in open_threads:
        score, reasons = rule_results[thread.thread_id]
        action = _action_for(score)
        if action == "NO_MATCH":
            continue
        candidates.append(MatchCandidate(
            thread_id=thread.thread_id,
            match_confidence=round(score, 2),
            reasons=reasons,
            recommended_action=action,
            relationship_type="COMPLETION_EVIDENCE" if completed_hint else "STATUS_UPDATE",
            closes_obligation=completed_hint and score >= 0.75,
            judged_by="rules",
        ))
    candidates.sort(key=lambda c: c.match_confidence, reverse=True)
    return candidates
