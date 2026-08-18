"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Check, X, ExternalLink } from "lucide-react";
import { api } from "@/lib/api";
import { StatusBadge, PriorityBadge } from "@/components/Badges";
import Avatar from "@/components/Avatar";
import IconTile, { toneForTitle } from "@/components/IconTile";
import { Stethoscope } from "lucide-react";
import type { ProposedAction, CareThread, Patient } from "@/lib/types";

interface Item {
  action: ProposedAction;
  thread: CareThread;
  patient: Patient;
}

const CHANGE_LABEL: Record<string, string> = {
  CLOSE_THREAD: "Close thread",
  ESCALATE_THREAD: "Escalate",
  EXTEND_DUE_DATE: "Extend deadline",
  LINK_EVIDENCE: "Link evidence",
  ASSIGN_OWNER: "Assign owner",
  OPEN_THREAD: "Open thread",
};

const CHANGE_TONE: Record<string, string> = {
  CLOSE_THREAD: "bg-violet-50 text-violet-700 ring-1 ring-inset ring-violet-200",
  ESCALATE_THREAD: "bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-200",
  EXTEND_DUE_DATE: "bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-200",
  LINK_EVIDENCE: "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-200",
  ASSIGN_OWNER: "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-200",
  OPEN_THREAD: "bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-200",
};

export default function ReviewQueue({ items }: { items: Item[] }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [selected, setSelected] = useState(0);

  function approve(id: string) {
    startTransition(async () => { await api.approveAction(id); router.refresh(); setSelected(0); });
  }
  function reject(id: string) {
    startTransition(async () => { await api.rejectAction(id, "Rejected by clinician"); router.refresh(); setSelected(0); });
  }

  if (items.length === 0) {
    return (
      <div className="mt-6 bg-white rounded-2xl border border-slate-200 p-10 text-center text-slate-400">
        Nothing awaiting review.
      </div>
    );
  }

  const item = items[Math.min(selected, items.length - 1)];

  return (
    <div className="grid grid-cols-3 gap-6 mt-6 items-start">
      <div className="col-span-2 bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="text-slate-400 text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-5 py-2.5 font-medium">Patient</th>
              <th className="text-left px-5 py-2.5 font-medium">Proposed change</th>
              <th className="text-left px-5 py-2.5 font-medium">Why</th>
              <th className="text-left px-5 py-2.5 font-medium">Owner</th>
              <th className="text-left px-5 py-2.5 font-medium">Priority</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it, idx) => (
              <tr
                key={it.action.action_id}
                onClick={() => setSelected(idx)}
                className={`border-t border-slate-100 cursor-pointer ${idx === selected ? "bg-blue-50" : "hover:bg-slate-50"}`}
              >
                <td className="px-5 py-3">
                  <div className="flex items-center gap-2.5">
                    <IconTile icon={Stethoscope} tone={toneForTitle(it.thread.title)} size={28} />
                    <div>
                      <div className="font-medium text-slate-800">{it.patient.display_name}</div>
                      <div className="text-xs text-slate-400">{it.thread.title}</div>
                    </div>
                  </div>
                </td>
                <td className="px-5 py-3">
                  <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${CHANGE_TONE[it.action.action_type] ?? "bg-slate-100 text-slate-600"}`}>
                    {CHANGE_LABEL[it.action.action_type] ?? it.action.action_type.replace(/_/g, " ")}
                  </span>
                </td>
                <td className="px-5 py-3 text-slate-500 max-w-xs truncate" title={it.action.reason}>{it.action.reason}</td>
                <td className="px-5 py-3 text-slate-600">{it.thread.owner_user_id?.replace(/_/g, " ") ?? "Unassigned"}</td>
                <td className="px-5 py-3"><PriorityBadge priority={it.thread.priority} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 p-5">
        <div className="flex items-center justify-between">
          <PriorityBadge priority={item.thread.priority} />
          <span className="text-xs text-slate-400 font-mono">{item.action.action_id}</span>
        </div>

        <div className="flex items-center gap-3 mt-4 pb-4 border-b border-slate-100">
          <Avatar name={item.patient.display_name} size={36} />
          <div className="flex-1 min-w-0">
            <div className="font-medium text-slate-800">{item.patient.display_name}</div>
            <div className="text-xs text-slate-500">MRN {item.patient.mrn}</div>
          </div>
          <Link href={`/threads/${item.thread.thread_id}`} className="text-slate-400 hover:text-teal-700">
            <ExternalLink size={15} />
          </Link>
        </div>

        <div className="mt-4">
          <div className="text-xs text-slate-400 uppercase tracking-wide mb-1.5">Proposed change</div>
          <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${CHANGE_TONE[item.action.action_type] ?? "bg-slate-100 text-slate-600"}`}>
            {CHANGE_LABEL[item.action.action_type] ?? item.action.action_type.replace(/_/g, " ")}
          </span>
        </div>

        <div className="mt-4">
          <div className="text-xs text-slate-400 uppercase tracking-wide mb-1.5">Rationale</div>
          <p className="text-sm text-slate-700 leading-relaxed">{item.action.reason}</p>
        </div>

        {item.action.action_type === "EXTEND_DUE_DATE" && (
          <div className="mt-4">
            <div className="text-xs text-slate-400 uppercase tracking-wide mb-1.5">Due date impact</div>
            <div className="text-sm text-slate-700 flex items-center gap-2">
              <span>{item.thread.due_at}</span>
              <span className="text-slate-400">→</span>
              <span className="text-emerald-700 font-medium">{String(item.action.proposed_payload.new_due_at)}</span>
            </div>
          </div>
        )}

        <div className="mt-4 pt-4 border-t border-slate-100 grid grid-cols-2 gap-3 text-sm">
          <div>
            <div className="text-xs text-slate-400">Owner</div>
            <div className="text-slate-700 mt-0.5">{item.thread.owner_user_id?.replace(/_/g, " ") ?? "Unassigned"}</div>
          </div>
          <div>
            <div className="text-xs text-slate-400">Requested on</div>
            <div className="text-slate-700 mt-0.5">{new Date(item.action.created_at).toLocaleDateString("en-US")}</div>
          </div>
        </div>

        <div className="mt-5 flex gap-2">
          <button
            disabled={pending}
            onClick={() => approve(item.action.action_id)}
            className="flex-1 flex items-center justify-center gap-1.5 rounded-lg bg-blue-600 text-white text-sm font-medium px-3 py-2 hover:bg-blue-700 disabled:opacity-40"
          >
            <Check size={15} /> Approve
          </button>
          <button
            disabled={pending}
            onClick={() => reject(item.action.action_id)}
            className="flex-1 flex items-center justify-center gap-1.5 rounded-lg border border-rose-200 text-rose-700 text-sm font-medium px-3 py-2 hover:bg-rose-50 disabled:opacity-40"
          >
            <X size={15} /> Reject
          </button>
        </div>

        <div className="mt-4 text-[11px] text-slate-400 text-center">
          All actions are logged for audit and compliance.
        </div>
      </div>
    </div>
  );
}
