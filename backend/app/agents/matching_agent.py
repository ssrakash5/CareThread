"""
Evidence matching agent (spec section 12). Deliberately not embeddings-only:
combines vector similarity with structured clinical signals so matches are
explainable to a clinician (spec section 13, Screen 3).

This is the "mock/rule-based agent" chosen for local dev in place of a
Bedrock-backed LLM judge. The output shape mirrors the agent output
contract in spec section 25 so a real LLM can be swapped in later without
touching callers.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CareThread, Finding, ThreadEvidence, Artifact
from app.ingestion.embeddings import cosine_similarity
from app.ingestion.extractors import extract_anatomical_location


@dataclass
class MatchCandidate:
    thread_id: str
    match_confidence: float
    reasons: List[str]
    recommended_action: str  # LINK_EVIDENCE | NEEDS_REVIEW | NO_MATCH


OPEN_STATUSES = {"OPEN", "IN_PROGRESS", "AWAITING_EVIDENCE", "OVERDUE", "ESCALATED"}


def find_candidate_threads(
    db: Session,
    patient_id: str,
    artifact: Artifact,
    chunk_texts: List[str],
    chunk_embeddings: List[List[float]],
) -> List[MatchCandidate]:
    """Patient-scoped only: never queries across patients."""
    open_threads = db.execute(
        select(CareThread).where(
            CareThread.patient_id == patient_id,
            CareThread.status.in_(OPEN_STATUSES),
        )
    ).scalars().all()

    full_text = " ".join(chunk_texts).lower()
    doc_location = extract_anatomical_location(full_text)

    candidates: List[MatchCandidate] = []
    for thread in open_threads:
        reasons = ["same patient"]
        score = 0.35  # same-patient scoping already narrows the space substantially

        finding = None
        if thread.finding_id:
            finding = db.get(Finding, thread.finding_id)

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
            from app.models import ArtifactChunk
            prior_chunk_ids = [e.chunk_id for e in prior_evidence if e.chunk_id]
            prior_chunks = db.execute(
                select(ArtifactChunk).where(ArtifactChunk.chunk_id.in_(prior_chunk_ids))
            ).scalars().all()
            for pc in prior_chunks:
                for emb in chunk_embeddings:
                    sim = cosine_similarity(emb, pc.embedding)
                    best_chunk_sim = max(best_chunk_sim, sim)
        if best_chunk_sim > 0.3:
            score += min(best_chunk_sim, 0.6) * 0.2
            reasons.append(f"semantic similarity to existing thread evidence ({best_chunk_sim:.2f})")

        score = min(score, 0.99)

        if score >= 0.75:
            action = "LINK_EVIDENCE"
        elif score >= 0.45:
            action = "NEEDS_REVIEW"
        else:
            continue  # not worth surfacing

        candidates.append(MatchCandidate(
            thread_id=thread.thread_id,
            match_confidence=round(score, 2),
            reasons=reasons,
            recommended_action=action,
        ))

    candidates.sort(key=lambda c: c.match_confidence, reverse=True)
    return candidates
