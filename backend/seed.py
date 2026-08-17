"""
Loads the synthetic demo dataset (spec section 29): a flagship patient
(Jane Doe) walked deeply through the full nodule follow-up lifecycle, a
couple of secondary patients, and distractor documents to prove retrieval
is patient-scoped and selective rather than a global semantic search.

Run: python seed.py
"""
from datetime import date

from sqlalchemy import text

from app.db import SessionLocal, engine, Base
from app.models import Patient, ProposedAction
from app.ingestion.pipeline import ingest_artifact
from app.workflows.approval_service import approve_action

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


def seed():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Reset for idempotent re-seeding in a demo environment.
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
        db.add_all([jane, marcus, elena])
        db.flush()

        print(f"Jane Doe -> {jane.patient_id}")
        print(f"Marcus Alvarez -> {marcus.patient_id}")
        print(f"Elena Petrova -> {elena.patient_id}")

        r1 = ingest_artifact(db, jane.patient_id, "RADIOLOGY_REPORT", "CT Chest Without Contrast",
                              JANE_RADIOLOGY, date(2026, 3, 12), "Radiology Associates")
        print("radiology ->", r1["proposed_actions"])

        r2 = ingest_artifact(db, jane.patient_id, "DISCHARGE_SUMMARY", "Hospital Discharge Summary",
                              JANE_DISCHARGE, date(2026, 3, 14), "General Hospital")
        print("discharge ->", r2["proposed_actions"])

        thread_id = r1.get("thread_id")
        db.commit()

        # Clinician approves the proposed thread (spec demo step: "clinician approves and assigns").
        open_action_id = r1["proposed_actions"][0]["action_id"]
        open_action = db.get(ProposedAction, open_action_id)
        approve_action(db, open_action, reviewer_id="dr_kapoor")
        db.commit()
        print(f"clinician approved thread {thread_id} -> status now OPEN/IN_PROGRESS")

        # Care coordinator assigned as owner.
        from app.models import CareThread
        from app.workflows.approval_service import _log_event
        thread = db.get(CareThread, thread_id)
        thread.owner_user_id = "katherine_lee"
        _log_event(db, thread_id, jane.patient_id, "OWNER_ASSIGNED", "dr_kapoor", thread.status, thread.status,
                   {"owner_user_id": "katherine_lee"})
        db.commit()
        print("assigned owner Katherine Lee")

        # distractors, ingested before the PCP note to prove patient-scoped retrieval
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
        print("pcp note ->", r3["proposed_actions"] or r3["match_candidates"])
        for pa in r3["proposed_actions"]:
            if pa["action_type"] == "LINK_EVIDENCE":
                approve_action(db, db.get(ProposedAction, pa["action_id"]), reviewer_id="katherine_lee")
        ingest_artifact(db, jane.patient_id, "PATIENT_MESSAGE", "Patient Portal Message",
                         JANE_MESSAGE, date(2026, 5, 10))
        db.commit()

        r4 = ingest_artifact(db, jane.patient_id, "RADIOLOGY_REPORT", "Follow-up CT Chest",
                              JANE_FOLLOWUP_CT, date(2026, 5, 20), "Radiology Associates")
        print("follow-up CT ->", r4["proposed_actions"] or r4["match_candidates"])
        for pa in r4["proposed_actions"]:
            approve_action(db, db.get(ProposedAction, pa["action_id"]), reviewer_id="dr_kapoor")
        db.commit()

        thread = db.get(CareThread, thread_id)
        print(f"\nFinal thread status: {thread.status} (closure_reason={thread.closure_reason})")

        print("\nSeed complete.")
        print(f"Flagship thread_id: {thread_id}")
        print(f"Jane Doe patient_id: {jane.patient_id}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
