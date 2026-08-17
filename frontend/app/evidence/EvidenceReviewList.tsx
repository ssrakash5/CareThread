"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Check, HelpCircle, X, ArrowLeftRight, ShieldCheck, FileText, Ban, UserCheck } from "lucide-react";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/Badges";
import Avatar from "@/components/Avatar";
import IconTile, { toneForTitle } from "@/components/IconTile";
import Ring from "@/components/Ring";
import type { ProposedAction, CareThread, Patient } from "@/lib/types";

interface Item {
  action: ProposedAction;
  thread: CareThread;
  patient: Patient;
}

const GUARDRAILS = [
  { icon: ShieldCheck, label: "Patient-scoped retrieval", desc: "Evidence is retrieved only within the selected patient's record." },
  { icon: FileText, label: "Evidence citations", desc: "All excerpts are sourced and citable to the original document." },
  { icon: Ban, label: "No automatic diagnosis", desc: "CareThread does not generate diagnoses or clinical decisions." },
  { icon: UserCheck, label: "Clinician approval required", desc: "Evidence is linked only after human review and approval." },
];

export default function EvidenceReviewList({ items }: { items: Item[] }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [selected, setSelected] = useState(0);

  if (items.length === 0) {
    return (
      <div className="mt-8 bg-white rounded-2xl border border-slate-200 p-10 text-center text-slate-400">
        No pending evidence matches. Ingest a new artifact for an existing patient to generate one.
      </div>
    );
  }

  const item = items[Math.min(selected, items.length - 1)];
  const reasons: string[] = item.action.reason.split(";").map((r) => r.trim()).filter(Boolean);
  const confidencePct = item.action.confidence * 100;

  function act(fn: () => Promise<unknown>) {
    startTransition(async () => { await fn(); router.refresh(); setSelected(0); });
  }

  return (
    <div className="grid grid-cols-4 gap-6 mt-6 items-start">
      <div className="bg-white rounded-2xl border border-slate-200 divide-y divide-slate-100 overflow-hidden">
        {items.map((it, idx) => (
          <button
            key={it.action.action_id}
            onClick={() => setSelected(idx)}
            className={`w-full text-left px-4 py-3 text-sm ${idx === selected ? "bg-blue-50" : "hover:bg-slate-50"}`}
          >
            <div className="flex items-center gap-2">
              <Avatar name={it.patient.display_name} size={22} />
              <div className="font-medium text-slate-800">{it.patient.display_name}</div>
            </div>
            <div className="text-xs text-slate-500 mt-1 truncate">{it.thread.title}</div>
            <div className="text-xs text-teal-700 mt-1 font-medium">{(it.action.confidence * 100).toFixed(0)}% match</div>
          </button>
        ))}
      </div>

      <div className="col-span-3 space-y-6">
        <div className="bg-white rounded-2xl border border-blue-100 ring-1 ring-blue-50 p-5 flex items-center gap-4">
          <IconTile icon={ArrowLeftRight} tone={toneForTitle(item.thread.title)} size={40} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <div className="font-semibold text-slate-900">{item.patient.display_name}</div>
              <StatusBadge status={item.thread.status} />
            </div>
            <div className="text-xs text-slate-500 mt-0.5">MRN {item.patient.mrn} · {item.thread.title}</div>
          </div>
          <Ring percent={confidencePct} size={44} />
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div className="bg-white rounded-2xl border border-slate-200 p-5">
            <div className="text-xs text-slate-400 uppercase tracking-wide mb-2">New evidence</div>
            <div className="text-sm font-medium text-slate-800">
              Artifact <span className="font-mono text-xs text-slate-500">{String(item.action.source_evidence.artifact_id)}</span>
            </div>
          </div>
          <div className="bg-white rounded-2xl border border-slate-200 p-5">
            <div className="text-xs text-slate-400 uppercase tracking-wide mb-2">Existing thread context</div>
            <Link href={`/threads/${item.thread.thread_id}`} className="text-sm font-medium text-teal-700 hover:underline">
              {item.thread.title}
            </Link>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-6">
          <div className="text-xs text-slate-400 uppercase tracking-wide mb-3">Match rationale</div>
          <ul className="space-y-2">
            {reasons.map((r, i) => (
              <li key={i} className="flex items-center gap-2 text-sm text-slate-700">
                <Check size={14} className="text-emerald-500 shrink-0" /> {r}
              </li>
            ))}
          </ul>
          <div className="mt-4 pt-4 border-t border-slate-100 text-sm font-medium text-slate-800">
            Match confidence <span className="text-teal-700">{confidencePct.toFixed(0)}%</span>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <button
              disabled={pending}
              onClick={() => act(() => api.approveAction(item.action.action_id))}
              className="flex items-center gap-1.5 rounded-lg bg-blue-600 text-white text-sm font-medium px-4 py-2 hover:bg-blue-700 disabled:opacity-40"
            >
              <Check size={15} /> Link to Thread
            </button>
            <button
              disabled={pending}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 text-slate-700 text-sm font-medium px-4 py-2 hover:bg-slate-50 disabled:opacity-40"
            >
              <HelpCircle size={15} /> Needs Human Review
            </button>
            <button
              disabled={pending}
              onClick={() => act(() => api.rejectAction(item.action.action_id, "Match rejected by clinician"))}
              className="flex items-center gap-1.5 rounded-lg border border-rose-200 text-rose-700 text-sm font-medium px-4 py-2 hover:bg-rose-50 disabled:opacity-40"
            >
              <X size={15} /> Reject Match
            </button>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-6">
          <div className="grid grid-cols-4 gap-4">
            {GUARDRAILS.map(({ icon: Icon, label, desc }) => (
              <div key={label} className="flex gap-2.5">
                <Icon size={16} className="text-slate-400 shrink-0 mt-0.5" />
                <div>
                  <div className="text-xs font-medium text-slate-800">{label}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
