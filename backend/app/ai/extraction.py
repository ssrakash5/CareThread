"""
Claude-backed clinical document extraction (replaces the regex extractor when
``CARETHREAD_AI_PROVIDER=bedrock``).

Returns the same ``ExtractedFact`` objects the rule-based path produces, plus
structured incidental findings so the pipeline can open follow-up threads for
any finding type, not only pulmonary nodules.
"""
from dataclasses import dataclass, field
from typing import List

from app.ai.bedrock import structured_call
from app.ingestion.extractors import ExtractedFact

FACT_TYPES = [
    "PULMONARY_NODULE_FINDING",   # kept for backward compatibility with the demo pipeline
    "INCIDENTAL_FINDING",
    "FOLLOWUP_RECOMMENDATION",
    "FOLLOWUP_COMPLETED",
    "STABLE_FINDING",
    "PROGRESSION_FINDING",
    "SCHEDULING_EVENT",
    "MEDICATION_CHANGE",
    "LAB_ABNORMALITY",
    "OTHER",
]


@dataclass
class ExtractedFinding:
    finding_type: str            # UPPER_SNAKE, e.g. PULMONARY_NODULE, THYROID_NODULE, AORTIC_ANEURYSM
    anatomical_location: str     # UPPER_SNAKE, e.g. RIGHT_UPPER_LOBE, LEFT_KIDNEY, "" if unknown
    description: str
    followup_recommended: bool = False
    followup_interval: str = ""  # e.g. "6-12 months", "4 weeks", "" if none


@dataclass
class ExtractionResult:
    facts: List[ExtractedFact] = field(default_factory=list)
    findings: List[ExtractedFinding] = field(default_factory=list)
    anatomical_location: str = ""


_SYSTEM = """You are a clinical document extraction engine inside CareThread, a system that
tracks incidental findings and their follow-up obligations across a patient's records.

Read one clinical document and extract structured facts. Be precise and conservative:
only report what the document actually states. Quote or closely paraphrase the source
text in fact_text. Use UPPER_SNAKE_CASE for finding types and anatomical locations
(e.g. PULMONARY_NODULE, THYROID_NODULE, AORTIC_ANEURYSM, RENAL_CYST, ACL_TEAR;
RIGHT_UPPER_LOBE, LEFT_KIDNEY, ASCENDING_AORTA, LEFT_FOREARM).

Fact type guidance:
- PULMONARY_NODULE_FINDING: a lung nodule is described. normalized_value = size like "6mm".
- INCIDENTAL_FINDING: any other incidental/actionable finding. normalized_value = finding type.
- FOLLOWUP_RECOMMENDATION: the document recommends follow-up imaging, testing, referral,
  biopsy or surveillance. normalized_value = the interval exactly as written but without
  spaces, e.g. "6-12months", "4weeks", "6months"; "" if no interval given.
- FOLLOWUP_COMPLETED: the document states a previously recommended follow-up study/visit
  was performed or completed.
- STABLE_FINDING / PROGRESSION_FINDING: a known finding is reported stable/unchanged or
  grown/worsened.
- SCHEDULING_EVENT: follow-up has been scheduled/booked (not yet completed).
- LAB_ABNORMALITY, MEDICATION_CHANGE, OTHER as appropriate.

Findings: list each incidental or clinically significant finding, most significant first.
Set followup_recommended=true only if THIS document recommends follow-up for that finding.
Do not invent findings from normal results ("within normal limits" is not a finding)."""

_SCHEMA = {
    "type": "object",
    "properties": {
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "fact_type": {"type": "string", "enum": FACT_TYPES},
                    "fact_text": {"type": "string"},
                    "normalized_value": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["fact_type", "fact_text", "normalized_value", "confidence"],
            },
        },
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "finding_type": {"type": "string"},
                    "anatomical_location": {"type": "string"},
                    "description": {"type": "string"},
                    "followup_recommended": {"type": "boolean"},
                    "followup_interval": {"type": "string"},
                },
                "required": ["finding_type", "anatomical_location", "description",
                             "followup_recommended", "followup_interval"],
            },
        },
        "primary_anatomical_location": {"type": "string"},
    },
    "required": ["facts", "findings", "primary_anatomical_location"],
}


def _norm(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in (s or "").strip().upper()).strip("_")


def extract_document_bedrock(text: str, artifact_type: str = "") -> ExtractionResult:
    data = structured_call(
        system=_SYSTEM,
        user=f"Document type: {artifact_type or 'UNKNOWN'}\n\n<document>\n{text}\n</document>",
        tool_name="record_extraction",
        tool_description="Record the structured facts and findings extracted from the document.",
        input_schema=_SCHEMA,
    )
    facts = [
        ExtractedFact(
            fact_type=f["fact_type"],
            fact_text=f["fact_text"].strip(),
            normalized_value=(f.get("normalized_value") or "").replace(" ", ""),
            confidence=max(0.0, min(1.0, float(f.get("confidence", 0.8)))),
        )
        for f in data.get("facts", [])
        if f.get("fact_text")
    ]
    findings = [
        ExtractedFinding(
            finding_type=_norm(f["finding_type"]),
            anatomical_location=_norm(f.get("anatomical_location", "")),
            description=f["description"].strip(),
            followup_recommended=bool(f.get("followup_recommended")),
            followup_interval=(f.get("followup_interval") or "").strip(),
        )
        for f in data.get("findings", [])
        if f.get("finding_type") and f.get("description")
    ]
    return ExtractionResult(
        facts=facts,
        findings=findings,
        anatomical_location=_norm(data.get("primary_anatomical_location", "")),
    )
