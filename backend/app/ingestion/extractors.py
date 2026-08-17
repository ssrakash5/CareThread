"""
Per-document-type extraction/chunking/fact-extraction, per spec section 24.

Each artifact_type gets a small extractor rather than one giant prompt.
Extraction here is regex/keyword based (mock agent reasoning, per project
decision to defer Bedrock until deployment).
"""
import re
from dataclasses import dataclass, field
from typing import List


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
