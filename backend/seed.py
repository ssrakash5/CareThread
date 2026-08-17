"""
Loads the synthetic demo dataset (spec section 29): a flagship patient
(Jane Doe) walked deeply through the full nodule follow-up lifecycle, a
couple of secondary/distractor patients to prove retrieval is
patient-scoped, plus several additional demo threads (cardiac, thyroid,
renal, spine) so the dashboard/review screens show realistic variety
instead of a single row. The additional threads are seeded directly
(not run through fact-extraction, which is nodule-specific) since they
exist to populate the UI, not to exercise the extraction regexes.

Run: python seed.py
"""
from datetime import date, datetime, timedelta

from sqlalchemy import text, select

from app.db import SessionLocal, engine, Base
from app.models import Patient, ProposedAction, CareThread, Finding, ArtifactChunk, ThreadEvidence
from app.ingestion.pipeline import ingest_artifact
from app.workflows.approval_service import approve_action, _log_event
from app.workflows.thread_state_machine import validate_transition

JANE_RADIOLOGY = """IMPRESSION:
6 mm solid pulmonary nodule in the right upper lobe, incidentally noted.
Follow-up CT chest recommended in 6-12 months per Fleischner criteria.

FINDINGS:
CT chest without contrast demonstrates a 6 mm solid pulmonary nodule in the right upper lobe.
No mediastinal or hilar lymphadenopathy. No pleural effusion.
"""

JANE_DISCHARGE = """DISCHARGE SUMMARY

HOSPITAL COURSE:
Patient admitted for evaluation of chest pain, ruled out for acute coronary syndrome.
CT chest performed during admission for further workup.

DISCHARGE INSTRUCTIONS:
Follow up with primary care physician in 2 weeks. Resume home medications.
Return to ED for worsening chest pain, shortness of breath, or fever.
"""

JANE_PCP_NOTE = """PROGRESS NOTE

SUBJECTIVE:
Patient here for routine follow-up. Reports feeling well overall.

ASSESSMENT/PLAN:
Reviewing prior imaging - noted pending recommendation for repeat CT chest
related to previously identified right upper lobe nodule. Will coordinate
scheduling of follow-up imaging.
"""

JANE_SCHEDULING_NOTE = """SCHEDULING UPDATE

Follow-up CT chest scheduled at Radiology Associates. Patient notified via
portal message and confirmed availability.
"""

JANE_FOLLOWUP_CT = """IMPRESSION:
Follow-up CT chest performed for prior incidentally noted right upper lobe pulmonary nodule.
6 mm solid pulmonary nodule in the right upper lobe, stable, unchanged from prior study.
No new nodules. No significant interval change.

FINDINGS:
Follow-up CT chest completed as recommended. Right upper lobe nodule stable in size and appearance.
"""

JANE_LAB = """LABORATORY RESULTS

CBC: WBC 6.8, Hgb 13.2, Plt 240 - within normal limits.
BMP: Na 140, K 4.1, Cr 0.9 - within normal limits.
"""

JANE_MESSAGE = """PATIENT MESSAGE

Hi, just confirming my appointment for the CT scan next month. Also wanted to ask
about refilling my blood pressure medication. Thanks!
"""

# Distractor documents, unrelated to the nodule thread, to prove retrieval is selective.
MARCUS_KNEE_MRI = """IMPRESSION:
Partial tear of the anterior cruciate ligament, left knee. No meniscal tear.
Recommend orthopedic surgery follow-up in 4-6 weeks.

FINDINGS:
MRI left knee without contrast shows partial-thickness ACL tear.
"""

MARCUS_ORTHO_NOTE = """PROGRESS NOTE

SUBJECTIVE:
Follow-up for left knee ACL partial tear. Pain improving with physical therapy.

ASSESSMENT/PLAN:
Continue PT. Re-image if symptoms worsen. No surgery planned at this time.
"""

ELENA_DERM_NOTE = """PROGRESS NOTE

SUBJECTIVE:
Patient presents with a changing mole on the left forearm.

ASSESSMENT/PLAN:
Suspicious pigmented lesion, left forearm. Recommend dermatology biopsy within 4 weeks.
"""


def first_chunk_id(db, artifact_id: str) -> str | None:
    chunk = db.execute(
        select(ArtifactChunk).where(ArtifactChunk.artifact_id == artifact_id).order_by(ArtifactChunk.chunk_index)
    ).scalars().first()
    return chunk.chunk_id if chunk else None


def build_demo_thread(
    db, patient, *, finding_type, location, description, thread_type, title,
    artifact_type, artifact_title, artifact_text, document_date, source_provider,
    owner, priority, due_at, target_status, follow_up_action=None,
):
    """Directly constructs a thread already OPEN/IN_PROGRESS (skipping the
    nodule-specific extraction pipeline) so the demo has varied finding
    types beyond pulmonary nodules. Still goes through the real approval
    service + state machine so audit events/history stay consistent."""
    result = ingest_artifact(db, patient.patient_id, artifact_type, artifact_title,
                              artifact_text, document_date, source_provider)
    db.flush()
    artifact_id = result["artifact_id"]
    chunk_id = first_chunk_id(db, artifact_id)

    finding = Finding(
        patient_id=patient.patient_id, finding_type=finding_type, anatomical_location=location,
        finding_description=description, source_artifact_id=artifact_id, source_chunk_id=chunk_id,
    )
    db.add(finding)
    db.flush()

    thread = CareThread(
        patient_id=patient.patient_id, thread_type=thread_type, title=title,
        finding_id=finding.finding_id, status="PROPOSED",
    )
    db.add(thread)
    db.flush()

    open_action = ProposedAction(
        thread_id=thread.thread_id, patient_id=patient.patient_id, action_type="OPEN_THREAD",
        proposed_payload={"title": title, "due_at": due_at.isoformat(), "priority": priority},
        reason=description, confidence=0.86,
        source_evidence={"artifact_id": artifact_id, "chunk_id": chunk_id},
    )
    db.add(open_action)
    db.flush()
    approve_action(db, open_action, reviewer_id="dr_kapoor")

    thread.owner_user_id = owner
    thread.priority = priority
    thread.due_at = due_at
    _log_event(db, thread.thread_id, patient.patient_id, "OWNER_ASSIGNED", "dr_kapoor", thread.status, thread.status,
               {"owner_user_id": owner})

    ev = ThreadEvidence(
        thread_id=thread.thread_id, artifact_id=artifact_id, chunk_id=chunk_id,
        relationship_type="INITIAL_FINDING", match_score=1.0, match_reason="Source finding for this thread.",
        linked_by="care_agent", approval_status="APPROVED",
    )
    db.add(ev)

    if target_status != thread.status:
        for step in _path_to(thread.status, target_status):
            validate_transition(thread.status, step)
            prev = thread.status
            thread.status = step
            _log_event(db, thread.thread_id, patient.patient_id, f"THREAD_{step}", "care_agent", prev, step)

    if follow_up_action:
        action_type, payload, reason, confidence = follow_up_action
        pending = ProposedAction(
            thread_id=thread.thread_id, patient_id=patient.patient_id, action_type=action_type,
            proposed_payload=payload, reason=reason, confidence=confidence,
            source_evidence={"artifact_id": artifact_id, "chunk_id": chunk_id},
        )
        db.add(pending)

    db.flush()
    return thread


def _path_to(current: str, target: str) -> list[str]:
    routes = {
        ("IN_PROGRESS", "AWAITING_EVIDENCE"): ["AWAITING_EVIDENCE"],
        ("IN_PROGRESS", "OVERDUE"): ["AWAITING_EVIDENCE", "OVERDUE"],
    }
    return routes.get((current, target), [target])


def seed():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        for table in ["thread_events", "proposed_actions", "thread_evidence", "care_threads",
                      "findings", "facts", "artifact_chunks", "artifacts", "patients"]:
            db.execute(text(f"DELETE FROM {table}"))
        db.commit()

        jane = Patient(mrn="MRN-100231", display_name="Jane Doe", dob=date(1965, 4, 2),
                        jurisdiction="US-CA", home_region="us-west-demo")
        marcus = Patient(mrn="MRN-100232", display_name="Marcus Alvarez", dob=date(1988, 11, 19),
                          jurisdiction="US-CA", home_region="us-west-demo")
        elena = Patient(mrn="MRN-100233", display_name="Elena Petrova", dob=date(1975, 7, 30),
                         jurisdiction="US-CA", home_region="us-west-demo")
        robert = Patient(mrn="MRN-100234", display_name="Robert Smith", dob=date(1953, 9, 4),
                          jurisdiction="US-CA", home_region="us-west-demo")
        maria = Patient(mrn="MRN-100235", display_name="Maria Garcia", dob=date(1958, 2, 17),
                         jurisdiction="US-CA", home_region="us-west-demo")
        james = Patient(mrn="MRN-100236", display_name="James Wilson", dob=date(1966, 12, 1),
                         jurisdiction="US-CA", home_region="us-west-demo")
        linda = Patient(mrn="MRN-100237", display_name="Linda Patel", dob=date(1961, 6, 23),
                         jurisdiction="US-CA", home_region="us-west-demo")
        db.add_all([jane, marcus, elena, robert, maria, james, linda])
        db.flush()
        for p in [jane, marcus, elena, robert, maria, james, linda]:
            print(f"{p.display_name} -> {p.patient_id}")

        # --- Jane Doe: full flagship lifecycle, driven by the real ingestion pipeline ---
        r1 = ingest_artifact(db, jane.patient_id, "RADIOLOGY_REPORT", "CT Chest Without Contrast",
                              JANE_RADIOLOGY, date(2026, 3, 12), "Radiology Associates")
        r2 = ingest_artifact(db, jane.patient_id, "DISCHARGE_SUMMARY", "Hospital Discharge Summary",
                              JANE_DISCHARGE, date(2026, 3, 14), "General Hospital")
        thread_id = r1.get("thread_id")
        db.commit()

        open_action = db.get(ProposedAction, r1["proposed_actions"][0]["action_id"])
        approve_action(db, open_action, reviewer_id="dr_kapoor")
        thread = db.get(CareThread, thread_id)
        thread.owner_user_id = "katherine_lee"
        thread.priority = "ROUTINE"
        _log_event(db, thread_id, jane.patient_id, "OWNER_ASSIGNED", "dr_kapoor", thread.status, thread.status,
                   {"owner_user_id": "katherine_lee"})
        db.commit()

        ingest_artifact(db, marcus.patient_id, "RADIOLOGY_REPORT", "MRI Left Knee",
                         MARCUS_KNEE_MRI, date(2026, 3, 15), "Orthopedic Imaging")
        ingest_artifact(db, marcus.patient_id, "PROGRESS_NOTE", "Ortho Follow-up",
                         MARCUS_ORTHO_NOTE, date(2026, 4, 1), "Sports Medicine Clinic")
        ingest_artifact(db, elena.patient_id, "PROGRESS_NOTE", "Dermatology Consult",
                         ELENA_DERM_NOTE, date(2026, 3, 20), "Dermatology Associates")
        db.commit()

        ingest_artifact(db, jane.patient_id, "LAB_RESULT", "Basic Metabolic Panel",
                         JANE_LAB, date(2026, 3, 12), "General Hospital")
        r3 = ingest_artifact(db, jane.patient_id, "PROGRESS_NOTE", "PCP Follow-up Visit",
                              JANE_PCP_NOTE, date(2026, 5, 7), "Primary Care Associates")
        for pa in r3["proposed_actions"]:
            if pa["action_type"] == "LINK_EVIDENCE":
                approve_action(db, db.get(ProposedAction, pa["action_id"]), reviewer_id="katherine_lee")
        ingest_artifact(db, jane.patient_id, "SCHEDULING_NOTE", "Scheduling Update",
                         JANE_SCHEDULING_NOTE, date(2026, 6, 24), "Northwell Imaging")
        ingest_artifact(db, jane.patient_id, "PATIENT_MESSAGE", "Patient Portal Message",
                         JANE_MESSAGE, date(2026, 5, 10))
        db.commit()

        # Follow-up CT arrives and matches — leave the resulting actions PENDING so
        # Jane shows up as a live example in Evidence Match Review / Clinician Review.
        r4 = ingest_artifact(db, jane.patient_id, "RADIOLOGY_REPORT", "Follow-up CT Chest",
                              JANE_FOLLOWUP_CT, date(2026, 6, 24), "Radiology Associates")
        print("follow-up CT ->", r4["proposed_actions"] or r4["match_candidates"])
        db.commit()

        # --- Additional demo threads for dashboard/review variety ---
        today = date.today()

        build_demo_thread(
            db, robert,
            finding_type="AORTIC_ANEURYSM", location="ASCENDING_AORTA",
            description="4.6 cm dilated ascending aorta, incidentally noted; recommend surveillance imaging in 6 months.",
            thread_type="CARDIAC_SURVEILLANCE", title="Dilated Ascending Aorta",
            artifact_type="RADIOLOGY_REPORT", artifact_title="CT Chest with Contrast",
            artifact_text="IMPRESSION:\nDilated ascending aorta measuring 4.6 cm. Recommend surveillance imaging in 6 months.",
            document_date=date(2026, 1, 18), source_provider="Cardiology Imaging",
            owner="aisha_malik", priority="URGENT", due_at=today - timedelta(days=6),
            target_status="OVERDUE",
            follow_up_action=("ESCALATE_THREAD", {"reason": "overdue_30_days"},
                               "Surveillance window exceeded by over 30 days; high-risk finding requires cardiology specialist review.",
                               0.9),
        )

        build_demo_thread(
            db, maria,
            finding_type="THYROID_NODULE", location="RIGHT_THYROID_LOBE",
            description="1.8 cm right thyroid nodule, incidentally noted; recommend ultrasound follow-up in 6 months.",
            thread_type="THYROID_FOLLOWUP", title="Thyroid Nodule",
            artifact_type="RADIOLOGY_REPORT", artifact_title="Neck Ultrasound",
            artifact_text="IMPRESSION:\n1.8 cm right thyroid nodule. Recommend follow-up ultrasound in 6 months.",
            document_date=date(2026, 6, 20), source_provider="Radiology Associates",
            owner="katherine_lee", priority="ROUTINE", due_at=today + timedelta(days=5),
            target_status="IN_PROGRESS",
        )

        build_demo_thread(
            db, james,
            finding_type="RENAL_CYST", location="LEFT_KIDNEY",
            description="2.1 cm simple left renal cyst, stable across two prior surveillance studies.",
            thread_type="RENAL_FOLLOWUP", title="Renal Cyst",
            artifact_type="RADIOLOGY_REPORT", artifact_title="Renal Ultrasound",
            artifact_text="IMPRESSION:\n2.1 cm simple left renal cyst, stable in size for 24 months compared to prior studies.",
            document_date=date(2026, 6, 17), source_provider="Radiology Associates",
            owner="andrew_chen", priority="ROUTINE", due_at=today + timedelta(days=11),
            target_status="IN_PROGRESS",
            follow_up_action=("CLOSE_THREAD", {"closure_reason": "stable_no_intervention"},
                               "Stable for 24 months across two surveillance studies; no intervention indicated.", 0.88),
        )

        build_demo_thread(
            db, linda,
            finding_type="LUMBAR_DEGENERATIVE_CHANGES", location="LUMBAR_SPINE",
            description="Moderate degenerative changes L4-L5; recommend conservative management and re-evaluation.",
            thread_type="SPINE_FOLLOWUP", title="Lumbar Degenerative Changes",
            artifact_type="RADIOLOGY_REPORT", artifact_title="Lumbar Spine MRI",
            artifact_text="IMPRESSION:\nModerate degenerative changes at L4-L5. Recommend conservative management with physical therapy.",
            document_date=date(2026, 6, 26), source_provider="Radiology Associates",
            owner="andrew_chen", priority="ROUTINE", due_at=today + timedelta(days=30),
            target_status="IN_PROGRESS",
            follow_up_action=("EXTEND_DUE_DATE", {"new_due_at": (today + timedelta(days=60)).isoformat()},
                               "Awaiting physical therapy scheduling availability; requesting 30-day extension.", 0.75),
        )

        db.commit()

        thread = db.get(CareThread, thread_id)
        print(f"\nJane Doe flagship thread status: {thread.status}")
        print("Seed complete.")
        print(f"Flagship thread_id: {thread_id}")
        print(f"Jane Doe patient_id: {jane.patient_id}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
