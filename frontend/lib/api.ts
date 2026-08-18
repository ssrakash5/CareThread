import type { Patient, Artifact, CareThread, ThreadEvent, ThreadEvidence, ProposedAction, Family, FamilyChatMessage, PatientChatMessage } from "./types";

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
  getPatientFamily: (id: string) => req<Family>(`/patients/${id}/family`),

  getPatientChat: (id: string) => req<PatientChatMessage[]>(`/patients/${id}/chat`),
  askPatientChat: (id: string, question: string) =>
    req<PatientChatMessage>(`/patients/${id}/chat`, { method: "POST", body: JSON.stringify({ question }) }),

  getFamily: (familyId: string) => req<Family>(`/families/${familyId}`),
  analyzeFamilyRisk: (familyId: string) =>
    req<ProposedAction[]>(`/families/${familyId}/analyze`, { method: "POST" }),

  getFamilyChat: (familyId: string) => req<FamilyChatMessage[]>(`/families/${familyId}/chat`),
  askFamilyChat: (familyId: string, question: string) =>
    req<FamilyChatMessage>(`/families/${familyId}/chat`, { method: "POST", body: JSON.stringify({ question }) }),

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

  uploadArtifact: async (
    patientId: string,
    payload: { file: File; artifact_type: string; title: string; document_date: string; source_provider?: string; caption?: string }
  ) => {
    const form = new FormData();
    form.append("file", payload.file);
    form.append("artifact_type", payload.artifact_type);
    form.append("title", payload.title);
    form.append("document_date", payload.document_date);
    form.append("source_provider", payload.source_provider ?? "");
    form.append("caption", payload.caption ?? "");
    const res = await fetch(`${BASE}/artifacts/${patientId}/upload`, {
      method: "POST",
      body: form,
      headers: { "X-User-Id": "dr_kapoor", "X-User-Role": "CLINICIAN" },
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Upload failed: ${res.status} ${body}`);
    }
    return res.json();
  },

  audit: (threadId: string) => req<ThreadEvent[]>(`/audit/threads/${threadId}`),
};
