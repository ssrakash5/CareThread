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

from app.config import settings
from app.db import SessionLocal, engine, Base, ensure_vector_support
from app.models import (
    Patient, ProposedAction, CareThread, Finding, ArtifactChunk, ThreadEvidence,
    FamilyGroup, FamilyRelationship,
)
from app.ingestion.pipeline import ingest_artifact
from app.workflows.approval_service import approve_action, _log_event
from app.workflows.thread_state_machine import validate_transition
from app.agents.family_agent import analyze_family
from app.ingestion.pdf_utils import extract_text_from_pdf
from demo_assets import make_pdf_bytes, make_ct_scan_png

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

JANE_PULMONOLOGY_CONSULT = """PULMONOLOGY CONSULT NOTE

REASON FOR VISIT:
Incidentally noted 6 mm right upper lobe pulmonary nodule, referred for surveillance planning.

ASSESSMENT/PLAN:
Nodule characteristics are low-risk per Fleischner criteria. Recommend follow-up CT chest
in 6-12 months as previously advised. Patient counseled on smoking cessation resources.
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
                              artifact_text, document_date, source_provider,
                              auto_propose_threads=False)  # thread is built by hand below
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
    ensure_vector_support()
    # Drop + recreate so schema changes (e.g. embedding_dim -> pgvector width)
    # take effect. This is a demo database; the seed is the source of truth.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print(f"AI provider: {settings.ai_provider}"
          + (f" ({settings.bedrock_model_id}, {settings.bedrock_embed_model_id}, dim={settings.embedding_dim})"
             if settings.ai_provider == "bedrock" else "")
          + f" | storage: {'s3://' + settings.s3_bucket if settings.s3_bucket else 'local disk'}")

    db = SessionLocal()
    try:

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

        # --- Family clusters (hereditary-risk demo) ---
        susan = Patient(mrn="MRN-100238", display_name="Susan Doe", dob=date(1968, 8, 14),
                         jurisdiction="US-CA", home_region="us-west-demo")
        michael = Patient(mrn="MRN-100239", display_name="Michael Doe", dob=date(1938, 3, 5),
                           jurisdiction="US-CA", home_region="us-west-demo")
        diego = Patient(mrn="MRN-100240", display_name="Diego Alvarez", dob=date(1990, 5, 22),
                         jurisdiction="US-CA", home_region="us-west-demo")
        sofia = Patient(mrn="MRN-100241", display_name="Sofia Alvarez", dob=date(1993, 9, 9),
                         jurisdiction="US-CA", home_region="us-west-demo")

        db.add_all([jane, marcus, elena, robert, maria, james, linda, susan, michael, diego, sofia])
        db.flush()
        for p in [jane, marcus, elena, robert, maria, james, linda, susan, michael, diego, sofia]:
            print(f"{p.display_name} -> {p.patient_id}")

        # --- Jane Doe: full flagship lifecycle, driven by the real ingestion pipeline ---
        print("Ingesting demo documents (each one runs extraction + matching)...")
        r1 = ingest_artifact(db, jane.patient_id, "RADIOLOGY_REPORT", "CT Chest Without Contrast",
                              JANE_RADIOLOGY, date(2026, 3, 12), "Radiology Associates")
        print("  Jane CT ->", r1["facts_extracted"], "| findings:", [f["finding_type"] for f in r1["findings_extracted"]],
              "| thread:", r1.get("thread_id"))
        if not r1.get("thread_id"):
            raise SystemExit("Seed aborted: the flagship CT report did not produce an OPEN_THREAD proposal. "
                             "Check extraction output above.")
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

        # --- Real PDF ingestion: generate a PDF, extract its text through the
        # same path a real upload would use, then run it through the normal
        # pipeline (chunk/embed/extract/match), storing the PDF bytes as the
        # artifact of record. ---
        consult_pdf = make_pdf_bytes("Pulmonology Consult Note", JANE_PULMONOLOGY_CONSULT)
        consult_text = extract_text_from_pdf(consult_pdf)
        r_pdf = ingest_artifact(db, jane.patient_id, "PROGRESS_NOTE", "Pulmonology Consult Note",
                                 consult_text, date(2026, 4, 20), "Pulmonology Associates",
                                 raw_bytes=consult_pdf, raw_ext="pdf", mime_type="application/pdf")
        print("  Jane pulmonology consult (PDF) ->", r_pdf["proposed_actions"] or r_pdf["match_candidates"])
        db.commit()

        # --- CT scan images: reference artifacts only (spec section 3) — stored,
        # captioned, and embedded for retrieval, never auto-interpreted. ---
        jane_scan_png = make_ct_scan_png()
        ingest_artifact(db, jane.patient_id, "IMAGE", "CT Chest - Axial Slice (RUL Nodule)",
                         "Axial CT chest slice, right upper lobe, showing the 6 mm nodule referenced "
                         "in the March 12 radiology report. Reference image only, not diagnostic.",
                         date(2026, 3, 12), "Radiology Associates",
                         raw_bytes=jane_scan_png, raw_ext="png", mime_type="image/png")
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

        # --- Family cluster 1: Doe family — hereditary pattern to flag ---
        doe_family = FamilyGroup(family_name="Doe Family")
        db.add(doe_family)
        db.flush()
        jane.family_id = doe_family.family_id
        susan.family_id = doe_family.family_id
        michael.family_id = doe_family.family_id
        db.add_all([
            FamilyRelationship(family_id=doe_family.family_id, patient_id=jane.patient_id,
                                related_patient_id=susan.patient_id, relationship_type="SIBLING"),
            FamilyRelationship(family_id=doe_family.family_id, patient_id=susan.patient_id,
                                related_patient_id=jane.patient_id, relationship_type="SIBLING"),
            FamilyRelationship(family_id=doe_family.family_id, patient_id=jane.patient_id,
                                related_patient_id=michael.patient_id, relationship_type="CHILD"),
            FamilyRelationship(family_id=doe_family.family_id, patient_id=michael.patient_id,
                                related_patient_id=jane.patient_id, relationship_type="PARENT"),
            FamilyRelationship(family_id=doe_family.family_id, patient_id=susan.patient_id,
                                related_patient_id=michael.patient_id, relationship_type="CHILD"),
            FamilyRelationship(family_id=doe_family.family_id, patient_id=michael.patient_id,
                                related_patient_id=susan.patient_id, relationship_type="PARENT"),
        ])

        # Susan shares Jane's exact finding (same type + location) so the family
        # agent has a genuine cross-relative pattern to detect.
        build_demo_thread(
            db, susan,
            finding_type="PULMONARY_NODULE", location="RIGHT_UPPER_LOBE",
            description="5 mm solid pulmonary nodule in the right upper lobe, incidentally noted; recommend follow-up CT in 6-12 months.",
            thread_type="INCIDENTAL_PULMONARY_FOLLOWUP", title="Incidental Pulmonary Nodule Follow-up",
            artifact_type="RADIOLOGY_REPORT", artifact_title="CT Chest Without Contrast",
            artifact_text="IMPRESSION:\n5 mm solid pulmonary nodule in the right upper lobe, incidentally noted. "
                          "Follow-up CT chest recommended in 6-12 months.",
            document_date=date(2026, 4, 2), source_provider="Radiology Associates",
            owner="katherine_lee", priority="ROUTINE", due_at=today + timedelta(days=180),
            target_status="IN_PROGRESS",
        )
        susan_scan_png = make_ct_scan_png(nodule_position=(0.6, 0.44))
        ingest_artifact(db, susan.patient_id, "IMAGE", "CT Chest - Axial Slice (RUL Nodule)",
                         "Axial CT chest slice, right upper lobe, showing Susan's 5 mm nodule. "
                         "Reference image only, not diagnostic.",
                         date(2026, 4, 2), "Radiology Associates",
                         raw_bytes=susan_scan_png, raw_ext="png", mime_type="image/png")
        db.commit()

        doe_pairs = analyze_family(db, doe_family.family_id)
        for hered_thread, hered_action in doe_pairs:
            db.add(hered_thread)
            db.flush()
            hered_action.thread_id = hered_thread.thread_id
            db.add(hered_action)
            db.flush()
            approve_action(db, hered_action, reviewer_id="dr_kapoor")
        db.commit()
        print(f"Doe family hereditary-risk flags: {len(doe_pairs)}")

        # --- Family cluster 2: Alvarez family — contrast case, no shared pattern ---
        alvarez_family = FamilyGroup(family_name="Alvarez Family")
        db.add(alvarez_family)
        db.flush()
        diego.family_id = alvarez_family.family_id
        sofia.family_id = alvarez_family.family_id
        db.add_all([
            FamilyRelationship(family_id=alvarez_family.family_id, patient_id=diego.patient_id,
                                related_patient_id=sofia.patient_id, relationship_type="SIBLING"),
            FamilyRelationship(family_id=alvarez_family.family_id, patient_id=sofia.patient_id,
                                related_patient_id=diego.patient_id, relationship_type="SIBLING"),
        ])

        build_demo_thread(
            db, diego,
            finding_type="THYROID_NODULE", location="LEFT_THYROID_LOBE",
            description="1.2 cm left thyroid nodule, incidentally noted; recommend ultrasound follow-up in 6 months.",
            thread_type="THYROID_FOLLOWUP", title="Thyroid Nodule",
            artifact_type="RADIOLOGY_REPORT", artifact_title="Neck Ultrasound",
            artifact_text="IMPRESSION:\n1.2 cm left thyroid nodule. Recommend follow-up ultrasound in 6 months.",
            document_date=date(2026, 5, 11), source_provider="Radiology Associates",
            owner="andrew_chen", priority="ROUTINE", due_at=today + timedelta(days=30),
            target_status="IN_PROGRESS",
        )
        build_demo_thread(
            db, sofia,
            finding_type="RENAL_CYST", location="RIGHT_KIDNEY",
            description="1.6 cm simple right renal cyst, incidentally noted; recommend surveillance in 12 months.",
            thread_type="RENAL_FOLLOWUP", title="Renal Cyst",
            artifact_type="RADIOLOGY_REPORT", artifact_title="Renal Ultrasound",
            artifact_text="IMPRESSION:\n1.6 cm simple right renal cyst. Recommend surveillance imaging in 12 months.",
            document_date=date(2026, 5, 14), source_provider="Radiology Associates",
            owner="andrew_chen", priority="ROUTINE", due_at=today + timedelta(days=45),
            target_status="IN_PROGRESS",
        )
        db.commit()

        alvarez_pairs = analyze_family(db, alvarez_family.family_id)
        print(f"Alvarez family hereditary-risk flags: {len(alvarez_pairs)} (expected 0 — no shared pattern)")

        thread = db.get(CareThread, thread_id)
        print(f"\nJane Doe flagship thread status: {thread.status}")
        print("Seed complete.")
        print(f"Flagship thread_id: {thread_id}")
        print(f"Jane Doe patient_id: {jane.patient_id}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
