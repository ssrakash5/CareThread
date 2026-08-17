"""
Document chunking + fact/finding extraction (spec section 24).

``extract_document`` is the entry point the pipeline uses. It dispatches on
``settings.ai_provider``:
  * ``bedrock`` -> Claude on Amazon Bedrock (app/ai/extraction.py) — general
    incidental-finding extraction for any document type.
  * ``local``   -> the regex/keyword extractor below (pulmonary-nodule focused,
    no network) — also the automatic fallback if the Bedrock call fails.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import List

from app.config import settings

log = logging.getLogger("carethread.extractors")


@dataclass
class ExtractedChunk:
    text: str
    section_name: str = ""
    page_number: int = 1


@dataclass
class ExtractedFact:
    fact_type: str
    fact_text: str
    normalized_value: str = ""
    confidence: float = 0.8


def chunk_text(text: str, max_chars: int = 500) -> List[ExtractedChunk]:
    """Split on section headers (ALL CAPS lines / blank-line paragraphs) then
    hard-wrap long paragraphs so each chunk stays retrieval-sized."""
    sections = re.split(r"\n\s*\n", text.strip())
    chunks: List[ExtractedChunk] = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        header_match = re.match(r"^([A-Z][A-Z /]{2,40}):?\s*\n", section)
        section_name = header_match.group(1).title() if header_match else ""
        body = section[header_match.end():] if header_match else section
        for i in range(0, len(body), max_chars):
            piece = body[i:i + max_chars].strip()
            if piece:
                chunks.append(ExtractedChunk(text=piece, section_name=section_name))
    return chunks or [ExtractedChunk(text=text.strip())]


_NODULE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s?mm\s+(solid|part[- ]solid|ground[- ]glass)?\s*(pulmonary )?nodule",
    re.IGNORECASE,
)
_LOCATION_RE = re.compile(
    r"(right|left)\s+(upper|middle|lower)\s+lobe", re.IGNORECASE
)
_FOLLOWUP_RE = re.compile(
    r"follow[- ]?up\s+(?:CT|imaging|chest CT)[^.\n]*?(\d+\s?(?:-|to)\s?\d+\s?months?|\d+\s?months?)",
    re.IGNORECASE,
)


def extract_facts(full_text: str) -> List[ExtractedFact]:
    facts: List[ExtractedFact] = []

    nodule = _NODULE_RE.search(full_text)
    if nodule:
        size, subtype, _ = nodule.groups()
        facts.append(ExtractedFact(
            fact_type="PULMONARY_NODULE_FINDING",
            fact_text=nodule.group(0).strip(),
            normalized_value=f"{size}mm",
            confidence=0.9,
        ))

    followup = _FOLLOWUP_RE.search(full_text)
    if followup:
        facts.append(ExtractedFact(
            fact_type="FOLLOWUP_RECOMMENDATION",
            fact_text=followup.group(0).strip(),
            normalized_value=followup.group(1).replace(" ", ""),
            confidence=0.9,
        ))

    if re.search(r"follow[- ]?up CT (chest )?completed|repeat CT (chest )?(was )?performed", full_text, re.I):
        facts.append(ExtractedFact(
            fact_type="FOLLOWUP_COMPLETED",
            fact_text="Follow-up imaging completed.",
            confidence=0.85,
        ))

    if re.search(r"stable|unchanged|no significant interval change", full_text, re.I):
        facts.append(ExtractedFact(
            fact_type="STABLE_FINDING",
            fact_text="Finding reported stable/unchanged.",
            confidence=0.7,
        ))

    return facts


def extract_anatomical_location(full_text: str) -> str:
    loc = _LOCATION_RE.search(full_text)
    if not loc:
        return ""
    return f"{loc.group(1).upper()}_{loc.group(2).upper()}_LOBE"


# ---------------------------------------------------------------------------
# Provider dispatch
# ---------------------------------------------------------------------------

def _local_extraction(full_text: str):
    """Wrap the regex extractor in the ExtractionResult shape the LLM path returns."""
    from app.ai.extraction import ExtractionResult, ExtractedFinding

    facts = extract_facts(full_text)
    location = extract_anatomical_location(full_text)
    findings = []
    nodule = next((f for f in facts if f.fact_type == "PULMONARY_NODULE_FINDING"), None)
    followup = next((f for f in facts if f.fact_type == "FOLLOWUP_RECOMMENDATION"), None)
    if nodule:
        findings.append(ExtractedFinding(
            finding_type="PULMONARY_NODULE",
            anatomical_location=location,
            description=nodule.fact_text,
            followup_recommended=followup is not None,
            followup_interval=followup.normalized_value if followup else "",
        ))
    return ExtractionResult(facts=facts, findings=findings, anatomical_location=location)


def extract_document(full_text: str, artifact_type: str = ""):
    """Return an ``ExtractionResult`` (facts + findings + primary location)."""
    if settings.ai_provider == "bedrock":
        try:
            from app.ai.extraction import extract_document_bedrock
            return extract_document_bedrock(full_text, artifact_type)
        except Exception as e:  # noqa: BLE001
            log.warning("Bedrock extraction failed (%s); using local extractor", e)
    return _local_extraction(full_text)
