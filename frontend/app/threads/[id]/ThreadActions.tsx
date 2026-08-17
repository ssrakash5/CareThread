"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { UserPlus, CalendarClock, TriangleAlert, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import type { CareThread } from "@/lib/types";

type Panel = "assign" | "extend" | null;

export default function ThreadActions({ thread }: { thread: CareThread }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [panel, setPanel] = useState<Panel>(null);
  const [owner, setOwner] = useState("");
  const [dueDate, setDueDate] = useState(thread.due_at ?? "");

  const canEscalate = !["CLOSED", "REJECTED", "ESCALATED"].includes(thread.status);

  function act(fn: () => Promise<unknown>) {
    startTransition(async () => { await fn(); router.refresh(); setPanel(null); });
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5">
      <div className="font-medium text-slate-800 mb-3 flex items-center gap-2">
        <ShieldCheck size={15} className="text-blue-600" /> Recommended actions
      </div>
      <div className="space-y-2">
        <button
          onClick={() => setPanel(panel === "assign" ? null : "assign")}
          className="w-full flex items-center gap-2.5 rounded-lg bg-blue-600 text-white text-sm font-medium px-3.5 py-2.5 hover:bg-blue-700"
        >
          <UserPlus size={15} /> Assign owner
        </button>
        {panel === "assign" && (
          <div className="flex gap-2 pl-1">
            <input
              autoFocus
              className="flex-1 border border-slate-300 rounded-md px-2.5 py-1.5 text-sm"
              placeholder="user id, e.g. katherine_lee"
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
            />
            <button
              disabled={pending || !owner}
              onClick={() => act(() => api.assignOwner(thread.thread_id, owner))}
              className="rounded-md bg-slate-800 text-white text-xs px-3 py-1.5 disabled:opacity-40"
            >
              Save
            </button>
          </div>
        )}

        <button
          onClick={() => setPanel(panel === "extend" ? null : "extend")}
          className="w-full flex items-center gap-2.5 rounded-lg border border-slate-200 text-slate-700 text-sm font-medium px-3.5 py-2.5 hover:bg-slate-50"
        >
          <CalendarClock size={15} /> Extend deadline
        </button>
        {panel === "extend" && (
          <div className="flex gap-2 pl-1">
            <input
              type="date"
              autoFocus
              className="flex-1 border border-slate-300 rounded-md px-2.5 py-1.5 text-sm"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
            <button
              disabled={pending || !dueDate}
              onClick={() => act(() => api.extendDueDate(thread.thread_id, dueDate))}
              className="rounded-md bg-slate-800 text-white text-xs px-3 py-1.5 disabled:opacity-40"
            >
              Save
            </button>
          </div>
        )}

        {canEscalate && (
          <button
            disabled={pending}
            onClick={() => act(() => api.escalate(thread.thread_id, "Manually escalated by clinician"))}
            className="w-full flex items-center gap-2.5 rounded-lg border border-rose-200 text-rose-700 text-sm font-medium px-3.5 py-2.5 hover:bg-rose-50 disabled:opacity-40"
          >
            <TriangleAlert size={15} /> Escalate
          </button>
        )}
      </div>
    </div>
  );
}
