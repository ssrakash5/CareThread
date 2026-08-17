"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { PriorityBadge } from "@/components/Badges";
import type { ProposedAction, CareThread, Patient } from "@/lib/types";

interface Item {
  action: ProposedAction;
  thread: CareThread;
  patient: Patient;
}

export default function ReviewQueue({ items }: { items: Item[] }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function approve(id: string) {
    startTransition(async () => { await api.approveAction(id); router.refresh(); });
  }
  function reject(id: string) {
    startTransition(async () => { await api.rejectAction(id, "Rejected by clinician"); router.refresh(); });
  }

  return (
    <div className="mt-6 bg-white rounded-xl border border-slate-200 overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wide">
          <tr>
            <th className="text-left px-5 py-2 font-medium">Patient</th>
            <th className="text-left px-5 py-2 font-medium">Thread</th>
            <th className="text-left px-5 py-2 font-medium">Proposed change</th>
            <th className="text-left px-5 py-2 font-medium">Reason</th>
            <th className="text-left px-5 py-2 font-medium">Owner</th>
            <th className="text-left px-5 py-2 font-medium">Priority</th>
            <th className="px-5 py-2" />
          </tr>
        </thead>
        <tbody>
          {items.map(({ action, thread, patient }) => (
            <tr key={action.action_id} className="border-t border-slate-100">
              <td className="px-5 py-3">{patient.display_name}</td>
              <td className="px-5 py-3">
                <Link href={`/threads/${thread.thread_id}`} className="text-teal-700 hover:underline">{thread.title}</Link>
              </td>
              <td className="px-5 py-3 font-medium">{action.action_type.replace(/_/g, " ")}</td>
              <td className="px-5 py-3 text-slate-500 max-w-xs truncate" title={action.reason}>{action.reason}</td>
              <td className="px-5 py-3 text-slate-600">{thread.owner_user_id ?? "Unassigned"}</td>
              <td className="px-5 py-3"><PriorityBadge priority={thread.priority} /></td>
              <td className="px-5 py-3">
                <div className="flex gap-2 justify-end">
                  <button disabled={pending} onClick={() => approve(action.action_id)} className="text-xs rounded-md bg-teal-600 text-white px-2.5 py-1.5 hover:bg-teal-700 disabled:opacity-40">Approve</button>
                  <button disabled={pending} onClick={() => reject(action.action_id)} className="text-xs rounded-md border border-red-300 text-red-700 px-2.5 py-1.5 hover:bg-red-50 disabled:opacity-40">Reject</button>
                </div>
              </td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr><td colSpan={7} className="px-5 py-10 text-center text-slate-400">Nothing awaiting review.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
