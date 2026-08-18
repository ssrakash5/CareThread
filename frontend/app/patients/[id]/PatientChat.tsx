"use client";

import { api } from "@/lib/api";
import ChatPanel from "@/components/ChatPanel";

export default function PatientChat({ patientId }: { patientId: string }) {
  return (
    <ChatPanel
      key={patientId}
      bordered={false}
      placeholder="e.g. What follow-up is still outstanding?"
      emptyHint="Answers are grounded only in this patient's own artifacts, findings, and threads — not a diagnosis."
      accentClass="bg-teal-600 hover:bg-teal-700"
      fetchHistory={() => api.getPatientChat(patientId)}
      ask={(q) => api.askPatientChat(patientId, q)}
    />
  );
}
