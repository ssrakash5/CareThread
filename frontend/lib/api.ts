import type { Patient, Artifact, CareThread, ThreadEvent, ThreadEvidence, ProposedAction } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      "X-User-Id": "dr_kapoor",
      "X-User-Role": "CLINICIAN",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${path} failed: ${res.status} ${body}`);
  }
  return res.json();
}

export const api = {
  listPatients: () => req<Patient[]>("/patients"),
  getPatient: (id: string) => req<Patient>(`/patients/${id}`),
  getPatientMemory: (id: string, artifactType?: string) =>
    req<Artifact[]>(`/patients/${id}/memory${artifactType ? `?artifact_type=${artifactType}` : ""}`),
  getPatientThreads: (id: string) => req<CareThread[]>(`/patients/${id}/threads`),

  listThreads: (status?: string) => req<CareThread[]>(`/threads${status ? `?status=${status}` : ""}`),
  getThread: (id: string) => req<CareThread>(`/threads/${id}`),
  getTimeline: (id: string) => req<ThreadEvent[]>(`/threads/${id}/timeline`),
  getEvidence: (id: string) => req<ThreadEvidence[]>(`/threads/${id}/evidence`),
  assignOwner: (id: string, owner_user_id: string) =>
    req<CareThread>(`/threads/${id}/assign`, { method: "POST", body: JSON.stringify({ owner_user_id }) }),
  extendDueDate: (id: string, new_due_at: string, reason = "") =>
    req<CareThread>(`/threads/${id}/extend`, { method: "POST", body: JSON.stringify({ new_due_at, reason }) }),
  escalate: (id: string, reason = "") =>
    req<CareThread>(`/threads/${id}/escalate`, { method: "POST", body: JSON.stringify({ reason }) }),

  listActions: (status = "PENDING") => req<ProposedAction[]>(`/actions?status=${status}`),
  approveAction: (id: string) => req<ProposedAction>(`/actions/${id}/approve`, { method: "POST" }),
  rejectAction: (id: string, reason = "") =>
    req<ProposedAction>(`/actions/${id}/reject`, { method: "POST", body: JSON.stringify({ reason }) }),

  ingestArtifact: (
    patientId: string,
    payload: { artifact_type: string; title: string; text: string; document_date: string; source_provider?: string }
  ) => req(`/artifacts/${patientId}`, { method: "POST", body: JSON.stringify(payload) }),

  audit: (threadId: string) => req<ThreadEvent[]>(`/audit/threads/${threadId}`),
};
