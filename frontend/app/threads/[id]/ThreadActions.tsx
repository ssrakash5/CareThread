"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { CareThread } from "@/lib/types";

export default function ThreadActions({ thread }: { thread: CareThread }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [owner, setOwner] = useState("");
  const [dueDate, setDueDate] = useState(thread.due_at ?? "");

  const canEscalate = !["CLOSED", "REJECTED", "ESCALATED"].includes(thread.status);

  return (
    <div className="mt-6 pt-6 border-t border-slate-100 flex flex-wrap items-end gap-3">
      <div>
        <label className="block text-xs text-slate-400 mb-1">Assign owner</label>
        <div className="flex gap-2">
          <input
            className="border border-slate-300 rounded-md px-2.5 py-1.5 text-sm w-40"
            placeholder="user id"
            value={owner}
            onChange={(e) => setOwner(e.target.value)}
          />
          <button
            disabled={pending || !owner}
            onClick={() => startTransition(async () => { await api.assignOwner(thread.thread_id, owner); router.refresh(); })}
            className="rounded-md bg-slate-800 text-white text-sm px-3 py-1.5 disabled:opacity-40"
          >
            Assign
          </button>
        </div>
      </div>

      <div>
        <label className="block text-xs text-slate-400 mb-1">Extend deadline</label>
        <div className="flex gap-2">
          <input
            type="date"
            className="border border-slate-300 rounded-md px-2.5 py-1.5 text-sm"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
          />
          <button
            disabled={pending || !dueDate}
            onClick={() => startTransition(async () => { await api.extendDueDate(thread.thread_id, dueDate); router.refresh(); })}
            className="rounded-md bg-slate-800 text-white text-sm px-3 py-1.5 disabled:opacity-40"
          >
            Extend
          </button>
        </div>
      </div>

      {canEscalate && (
        <button
          disabled={pending}
          onClick={() => startTransition(async () => { await api.escalate(thread.thread_id, "Manually escalated by clinician"); router.refresh(); })}
          className="rounded-md border border-red-300 text-red-700 text-sm px-3 py-1.5 hover:bg-red-50 disabled:opacity-40"
        >
          Escalate
        </button>
      )}
    </div>
  );
}
