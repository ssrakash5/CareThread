"""
Claude-backed evidence-matching judge. Given a new document and the patient's
open care threads (plus the rule-based signals already computed), decide for
each thread whether the document is evidence for it and how it relates.
"""
from typing import Any, Dict, List

from app.ai.bedrock import structured_call

_SYSTEM = """You are the evidence-matching judge inside CareThread. A care thread tracks one
outstanding follow-up obligation for a patient (e.g. "repeat CT chest for a 6 mm right
upper lobe nodule in 6-12 months"). A new clinical document for the SAME patient has
arrived. For each open thread, decide whether this document is evidence about that
thread's finding/obligation.

For each thread return:
- match_confidence: 0.0-1.0 that the document concerns this thread's finding.
- recommended_action:
    LINK_EVIDENCE  - clearly about this thread (confidence >= 0.75)
    NEEDS_REVIEW   - plausibly related, a clinician should confirm (0.45-0.75)
    NO_MATCH       - unrelated
- relationship_type:
    COMPLETION_EVIDENCE - the recommended follow-up study/visit was actually performed
    STATUS_UPDATE       - scheduling, discussion, planning, or interim mention
    NEW_INFORMATION     - the finding changed (progression/resolution) but obligation unclear
    UNRELATED
- reasons: 1-4 short, clinician-readable phrases explaining the judgment
  (e.g. "same right upper lobe nodule", "follow-up CT completed", "different organ system").
- closes_obligation: true only if this document shows the thread's follow-up obligation
  has been fulfilled (e.g. the recommended repeat imaging was done).

Be conservative: mentioning a follow-up being scheduled is STATUS_UPDATE, not completion.
Judge each thread independently. Rule-based signals are hints, not ground truth."""

_SCHEMA = {
    "type": "object",
    "properties": {
        "judgments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string"},
                    "match_confidence": {"type": "number"},
                    "recommended_action": {"type": "string", "enum": ["LINK_EVIDENCE", "NEEDS_REVIEW", "NO_MATCH"]},
                    "relationship_type": {"type": "string",
                                          "enum": ["COMPLETION_EVIDENCE", "STATUS_UPDATE", "NEW_INFORMATION", "UNRELATED"]},
                    "reasons": {"type": "array", "items": {"type": "string"}},
                    "closes_obligation": {"type": "boolean"},
                },
                "required": ["thread_id", "match_confidence", "recommended_action",
                             "relationship_type", "reasons", "closes_obligation"],
            },
        }
    },
    "required": ["judgments"],
}


def judge_matches_bedrock(
    document_text: str,
    artifact_type: str,
    threads: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """``threads``: [{thread_id, title, status, finding_type, anatomical_location,
    finding_description, due_at, rule_signals: [str]}]. Returns one judgment per
    thread_id (threads the model omits are treated as NO_MATCH by the caller)."""
    if not threads:
        return []
    thread_block = "\n".join(
        f"- thread_id: {t['thread_id']}\n"
        f"  title: {t.get('title','')}\n"
        f"  status: {t.get('status','')}\n"
        f"  finding: {t.get('finding_type','') or 'n/a'} @ {t.get('anatomical_location','') or 'n/a'}\n"
        f"  description: {t.get('finding_description','') or 'n/a'}\n"
        f"  due: {t.get('due_at','') or 'n/a'}\n"
        f"  rule_signals: {', '.join(t.get('rule_signals') or []) or 'none'}"
        for t in threads
    )
    user = (
        f"Document type: {artifact_type or 'UNKNOWN'}\n\n"
        f"<document>\n{document_text}\n</document>\n\n"
        f"<open_threads>\n{thread_block}\n</open_threads>\n\n"
        "Return one judgment for every thread_id listed."
    )
    data = structured_call(
        system=_SYSTEM,
        user=user,
        tool_name="record_judgments",
        tool_description="Record the evidence-matching judgment for each open thread.",
        input_schema=_SCHEMA,
    )
    out = []
    for j in data.get("judgments", []):
        j["match_confidence"] = max(0.0, min(0.99, float(j.get("match_confidence", 0))))
        j["reasons"] = [r for r in (j.get("reasons") or []) if r][:4]
        out.append(j)
    return out
