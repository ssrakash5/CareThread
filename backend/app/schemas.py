from datetime import date, datetime
from typing import Optional, List, Any

from pydantic import BaseModel


class PatientOut(BaseModel):
    patient_id: str
    mrn: str
    display_name: str
    dob: date
    jurisdiction: str
    home_region: str

    class Config:
        from_attributes = True


class PatientCreate(BaseModel):
    mrn: str
    display_name: str
    dob: date
    jurisdiction: str = "US-GENERIC"
    home_region: str = "us-demo"


class ArtifactIngest(BaseModel):
    artifact_type: str
    title: str
    text: str
    document_date: date
    source_provider: str = ""


class ArtifactOut(BaseModel):
    artifact_id: str
    patient_id: str
    artifact_type: str
    title: str
    document_date: date
    source_provider: str
    status: str
    s3_uri: str
    created_at: datetime

    class Config:
        from_attributes = True


class ThreadOut(BaseModel):
    thread_id: str
    patient_id: str
    thread_type: str
    title: str
    finding_id: Optional[str]
    status: str
    priority: str
    owner_user_id: Optional[str]
    due_at: Optional[date]
    opened_at: Optional[datetime]
    closed_at: Optional[datetime]
    closure_reason: Optional[str]

    class Config:
        from_attributes = True


class ThreadEventOut(BaseModel):
    event_id: str
    event_type: str
    actor_type: str
    actor_id: str
    previous_state: Optional[str]
    new_state: Optional[str]
    event_metadata: dict
    created_at: datetime

    class Config:
        from_attributes = True


class ThreadEvidenceOut(BaseModel):
    thread_evidence_id: str
    artifact_id: str
    chunk_id: Optional[str]
    relationship_type: str
    match_score: float
    match_reason: str
    approval_status: str
    linked_at: datetime

    class Config:
        from_attributes = True


class ProposedActionOut(BaseModel):
    action_id: str
    thread_id: str
    patient_id: str
    action_type: str
    proposed_payload: dict
    reason: str
    confidence: float
    source_evidence: dict
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime]
    reviewed_by: Optional[str]

    class Config:
        from_attributes = True


class AssignRequest(BaseModel):
    owner_user_id: str


class ExtendRequest(BaseModel):
    new_due_at: date
    reason: str = ""


class EscalateRequest(BaseModel):
    reason: str = ""


class RejectRequest(BaseModel):
    reason: str = ""


class IngestResult(BaseModel):
    artifact_id: str
    chunks_created: int
    facts_extracted: List[str]
    proposed_actions: List[dict]
    match_candidates: List[dict]
    thread_id: Optional[str] = None
