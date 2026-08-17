"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Check, HelpCircle, X } from "lucide-react";
import { api } from "@/lib/api";
import type { ProposedAction, CareThread, Patient } from "@/lib/types";

interface Item {
  action: ProposedAction;
  thread: CareThread;
  patient: Patient;
}

export default function EvidenceReviewList({ items }: { items: Item[] }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [selected, setSelected] = useState(0);

  if (items.length === 0) {
    return (
      <div className="mt-8 bg-white rounded-xl border border-slate-200 p-10 text-center text-slate-400">
        No pending evidence matches. Ingest a new artifact for an existing patient to generate one.
      </div>
    );
  }

  const item = items[Math.min(selected, items.length - 1)];
  const reasons: string[] = item.action.reason.split(";").map((r) => r.trim()).filter(Boolean);

  function act(fn: () => Promise<unknown>) {
    startTransition(async () => {
      await fn();
      router.refresh();
      setSelected(0);
    });
  }

  return (
    <div className="grid grid-cols-3 gap-6 mt-6">
      <div className="bg-white rounded-xl border border-slate-200 divide-y divide-slate-100">
        {items.map((it, idx) => (
          <button
            key={it.action.action_id}
            onClick={() => setSelected(idx)}
            className={`w-full text-left px-4 py-3 text-sm ${idx === selected ? "bg-teal-50" : "hover:bg-slate-50"}`}
          >
            <div className="font-medium text-slate-800">{it.patient.display_name}</div>
            <div className="text-xs text-slate-500 mt-0.5">{it.thread.title}</div>
            <div className="text-xs text-teal-700 mt-1">{(it.action.confidence * 100).toFixed(0)}% match</div>
          </button>
        ))}
      </div>

      <div className="col-span-2 bg-white rounded-xl border border-slate-200 p-6">
        <div className="grid grid-cols-2 gap-6">
          <div>
            <div className="text-xs text-slate-400 uppercase tracking-wide mb-1">New evidence</div>
            <div className="text-sm text-slate-700">
              Artifact <span className="font-mono text-xs">{String(item.action.source_evidence.artifact_id)}</span>
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-400 uppercase tracking-wide mb-1">Existing CareThread</div>
            <Link href={`/threads/${item.thread.thread_id}`} className="text-sm text-teal-700 hover:underline">
              {item.thread.title}
            </Link>
          </div>
        </div>

        <div className="mt-6">
          <div className="text-xs text-slate-400 uppercase tracking-wide mb-2">Match explanation</div>
          <ul className="space-y-1.5">
            {reasons.map((r, i) => (
              <li key={i} className="flex items-center gap-2 text-sm text-slate-700">
                <Check size={14} className="text-emerald-500" /> {r}
              </li>
            ))}
          </ul>
          <div className="mt-3 text-sm font-medium">
            Match confidence <span className="text-teal-700">{(item.action.confidence * 100).toFixed(0)}%</span>
          </div>
        </div>

        <div className="mt-6 pt-6 border-t border-slate-100 flex gap-3">
          <button
            disabled={pending}
            onClick={() => act(() => api.approveAction(item.action.action_id))}
            className="flex items-center gap-1.5 rounded-md bg-teal-600 text-white text-sm px-3.5 py-2 hover:bg-teal-700 disabled:opacity-40"
          >
            <Check size={15} /> Link to Thread
          </button>
          <button
            disabled={pending}
            className="flex items-center gap-1.5 rounded-md border border-slate-300 text-slate-700 text-sm px-3.5 py-2 hover:bg-slate-50 disabled:opacity-40"
          >
            <HelpCircle size={15} /> Needs Human Review
          </button>
          <button
            disabled={pending}
            onClick={() => act(() => api.rejectAction(item.action.action_id, "Match rejected by clinician"))}
            className="flex items-center gap-1.5 rounded-md border border-red-300 text-red-700 text-sm px-3.5 py-2 hover:bg-red-50 disabled:opacity-40"
          >
            <X size={15} /> Reject Match
          </button>
        </div>
      </div>
    </div>
  );
}
