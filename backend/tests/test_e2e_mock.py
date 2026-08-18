"""
Full MVP "definition of done" walk (project.md section 33), mock/local
provider throughout, driven entirely through the HTTP API (each request is
its own short-lived transaction — avoids overlapping-session serialization
conflicts against CockroachDB's SERIALIZABLE isolation):
ingest -> thread proposed -> approve -> assign -> new evidence ingested ->
matched & linked -> closure proposed & approved -> full provenance visible.
"""
RADIOLOGY = """IMPRESSION:
6 mm solid pulmonary nodule in the right upper lobe, incidentally noted.
Follow-up CT chest recommended in 6-12 months per Fleischner criteria.
"""

FOLLOWUP_CT = """IMPRESSION:
Follow-up CT chest performed for prior incidentally noted right upper lobe pulmonary nodule.
6 mm solid pulmonary nodule in the right upper lobe, stable, unchanged from prior study.
Follow-up CT chest completed as recommended.
"""


def test_full_definition_of_done_sequence(client):
    resp = client.post("/patients", json={
        "mrn": "MRN-E2E-001", "display_name": "E2E Test Patient", "dob": "1970-01-01",
    })
    assert resp.status_code == 200
    patient_id = resp.json()["patient_id"]

    resp = client.post(f"/artifacts/{patient_id}", json={
        "artifact_type": "RADIOLOGY_REPORT", "title": "CT Chest", "text": RADIOLOGY,
        "document_date": "2026-01-01", "source_provider": "Test Radiology",
    })
    assert resp.status_code == 200
    result = resp.json()
    assert result.get("thread_id"), f"expected an OPEN_THREAD proposal, got: {result}"
    thread_id = result["thread_id"]
    open_action_id = result["proposed_actions"][0]["action_id"]

    assert client.get(f"/threads/{thread_id}").json()["status"] == "PROPOSED"

    resp = client.post(f"/actions/{open_action_id}/approve")
    assert resp.status_code == 200
    assert client.get(f"/threads/{thread_id}").json()["status"] == "IN_PROGRESS"

    resp = client.post(f"/threads/{thread_id}/assign", json={"owner_user_id": "katherine_lee"})
    assert resp.status_code == 200
    assert resp.json()["owner_user_id"] == "katherine_lee"

    resp = client.post(f"/artifacts/{patient_id}", json={
        "artifact_type": "RADIOLOGY_REPORT", "title": "Follow-up CT Chest", "text": FOLLOWUP_CT,
        "document_date": "2026-07-01", "source_provider": "Test Radiology",
    })
    assert resp.status_code == 200
    followup = resp.json()
    assert followup["match_candidates"], "expected the follow-up CT to match the open thread"

    link_actions = [a for a in followup["proposed_actions"] if a["action_type"] == "LINK_EVIDENCE"]
    assert link_actions, f"expected a LINK_EVIDENCE proposal, got: {followup['proposed_actions']}"
    resp = client.post(f"/actions/{link_actions[0]['action_id']}/approve")
    assert resp.status_code == 200

    resp = client.get(f"/threads/{thread_id}/evidence")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    close_actions = [a for a in followup["proposed_actions"] if a["action_type"] == "CLOSE_THREAD"]
    assert close_actions, f"expected a CLOSE_THREAD proposal, got: {followup['proposed_actions']}"
    resp = client.post(f"/actions/{close_actions[0]['action_id']}/approve")
    assert resp.status_code == 200

    assert client.get(f"/threads/{thread_id}").json()["status"] == "CLOSED"

    resp = client.get(f"/threads/{thread_id}/timeline")
    assert resp.status_code == 200
    event_types = {e["event_type"] for e in resp.json()}
    assert {"THREAD_OPENED", "THREAD_IN_PROGRESS", "OWNER_ASSIGNED",
            "EVIDENCE_LINKED", "CLOSURE_PROPOSED", "THREAD_CLOSED"} <= event_types
