"use client";

import { api } from "@/lib/api";
import ChatPanel from "@/components/ChatPanel";

export default function FamilyChat({ familyId }: { familyId: string }) {
  return (
    <ChatPanel
      key={familyId}
      label="Ask about this family"
      placeholder="e.g. Which relatives share a finding?"
      emptyHint="Answers are grounded only in this family's documented findings and relationships — not a diagnosis."
      accentClass="bg-purple-600 hover:bg-purple-700"
      fetchHistory={() => api.getFamilyChat(familyId)}
      ask={(q) => api.askFamilyChat(familyId, q)}
    />
  );
}
