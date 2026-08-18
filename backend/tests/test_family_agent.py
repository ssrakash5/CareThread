"""Family clusters / hereditary-risk agent: shared pattern flags, no false positives."""
from datetime import date

from app.config import settings
from app.models import Patient, FamilyGroup, FamilyRelationship, Finding, Artifact, ArtifactChunk
from app.agents.family_agent import analyze_family


def _patient(mrn, name):
    return Patient(mrn=mrn, display_name=name, dob=date(1970, 1, 1))


def _finding(db, patient, finding_type, location, description):
    """Finding.source_artifact_id/source_chunk_id are FK-constrained (not
    nullable), so tests need real Artifact/ArtifactChunk rows behind them."""
    artifact = Artifact(patient_id=patient.patient_id, artifact_type="RADIOLOGY_REPORT",
                         document_date=date(2026, 1, 1), s3_uri="local://test", title="Test Report")
    db.add(artifact)
    db.flush()
    chunk = ArtifactChunk(artifact_id=artifact.artifact_id, patient_id=patient.patient_id,
                           chunk_index=0, chunk_text=description,
                           embedding=[0.0] * settings.embedding_dim)
    db.add(chunk)
    db.flush()
    finding = Finding(patient_id=patient.patient_id, finding_type=finding_type,
                       anatomical_location=location, finding_description=description,
                       source_artifact_id=artifact.artifact_id, source_chunk_id=chunk.chunk_id)
    db.add(finding)
    return finding


def test_flags_shared_finding_across_relatives(db):
    jane = _patient("MRN-FAM-001", "Jane Test")
    susan = _patient("MRN-FAM-002", "Susan Test")
    db.add_all([jane, susan])
    db.flush()

    group = FamilyGroup(family_name="Test Family")
    db.add(group)
    db.flush()
    jane.family_id = group.family_id
    susan.family_id = group.family_id
    db.add(FamilyRelationship(family_id=group.family_id, patient_id=jane.patient_id,
                               related_patient_id=susan.patient_id, relationship_type="SIBLING"))

    _finding(db, jane, "PULMONARY_NODULE", "RIGHT_UPPER_LOBE", "6mm nodule")
    _finding(db, susan, "PULMONARY_NODULE", "RIGHT_UPPER_LOBE", "5mm nodule")
    db.commit()

    pairs = analyze_family(db, group.family_id)
    assert len(pairs) == 1
    thread, action = pairs[0]
    assert thread.thread_type == "HEREDITARY_RISK_REVIEW"
    assert action.action_type == "OPEN_THREAD"
    assert action.proposed_payload["family_id"] == group.family_id


def test_no_flag_without_shared_pattern(db):
    diego = _patient("MRN-FAM-003", "Diego Test")
    sofia = _patient("MRN-FAM-004", "Sofia Test")
    db.add_all([diego, sofia])
    db.flush()

    group = FamilyGroup(family_name="Contrast Family")
    db.add(group)
    db.flush()
    diego.family_id = group.family_id
    sofia.family_id = group.family_id

    _finding(db, diego, "THYROID_NODULE", "LEFT_THYROID_LOBE", "nodule")
    _finding(db, sofia, "RENAL_CYST", "RIGHT_KIDNEY", "cyst")
    db.commit()

    assert analyze_family(db, group.family_id) == []
