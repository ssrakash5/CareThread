import Link from "next/link";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/Badges";
import Avatar from "@/components/Avatar";
import Ring from "@/components/Ring";
import IconTile, { toneForTitle } from "@/components/IconTile";
import { CheckCircle2, Inbox, FileClock, AlertTriangle, FileCheck2, Stethoscope } from "lucide-react";
import CheckOverdueButton from "./CheckOverdueButton";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const [threads, patients, pendingActions] = await Promise.all([
    api.listThreads(),
    api.listPatients(),
    api.listActions("PENDING"),
  ]);

  const patientById = Object.fromEntries(patients.map((p) => [p.patient_id, p]));

  const openThreads = threads.filter((t) =>
    ["OPEN", "IN_PROGRESS", "AWAITING_EVIDENCE", "OVERDUE", "ESCALATED"].includes(t.status)
  );
  const overdue = threads.filter((t) => t.status === "OVERDUE" || t.status === "ESCALATED");

  const matchByThread: Record<string, number> = {};
  for (const a of pendingActions) {
    if (a.action_type === "LINK_EVIDENCE") {
      matchByThread[a.thread_id] = Math.max(matchByThread[a.thread_id] ?? 0, a.confidence * 100);
    }
  }

  const sortedThreads = [...threads].sort((a, b) => (b.opened_at || "").localeCompare(a.opened_at || ""));

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
          <p className="text-slate-500 mt-1 text-sm">Operational inbox for unresolved care obligations.</p>
        </div>
        <CheckOverdueButton />
      </div>

      <div className="grid grid-cols-4 gap-4 mt-6">
        <StatTile icon={Inbox} label="Open Threads" value={openThreads.length} tone="blue" />
        <StatTile icon={FileCheck2} label="Needs Review" value={pendingActions.length} tone="amber" />
        <StatTile icon={AlertTriangle} label="Overdue Follow-ups" value={overdue.length} tone="rose" />
        <StatTile icon={FileClock} label="Total Threads" value={threads.length} tone="teal" />
      </div>

      <div className="grid grid-cols-3 gap-6 mt-6">
        <div className="col-span-2 bg-white rounded-2xl border border-slate-200">
          <div className="px-5 py-4 border-b border-slate-100 font-medium text-slate-800">
            Proposed / Open Care Threads <span className="text-slate-400 font-normal">{threads.length}</span>
          </div>
          <table className="w-full text-sm">
            <thead className="text-slate-400 text-xs uppercase tracking-wide">
              <tr>
                <th className="text-left px-5 py-2.5 font-medium">Patient</th>
                <th className="text-left px-5 py-2.5 font-medium">Finding / Thread type</th>
                <th className="text-left px-5 py-2.5 font-medium">Status</th>
                <th className="text-left px-5 py-2.5 font-medium">Owner</th>
                <th className="text-left px-5 py-2.5 font-medium">Due date</th>
                <th className="text-right px-5 py-2.5 font-medium">Evidence match</th>
              </tr>
            </thead>
            <tbody>
              {sortedThreads.map((t) => {
                const patient = patientById[t.patient_id];
                return (
                  <tr key={t.thread_id} className="border-t border-slate-100 hover:bg-slate-50">
                    <td className="px-5 py-3">
                      <Link href={`/threads/${t.thread_id}`} className="flex items-center gap-2.5">
                        <Avatar name={patient?.display_name ?? t.patient_id} size={26} />
                        <span className="font-medium text-slate-800 hover:text-teal-700">
                          {patient?.display_name ?? t.patient_id}
                        </span>
                      </Link>
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2.5">
                        <IconTile icon={Stethoscope} tone={toneForTitle(t.title)} size={30} />
                        <span className="text-slate-700">{t.title}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3"><StatusBadge status={t.status} /></td>
                    <td className="px-5 py-3">
                      {t.owner_user_id ? (
                        <div className="flex items-center gap-2">
                          <Avatar name={t.owner_user_id} size={22} />
                          <span className="text-slate-600 text-xs">{t.owner_user_id.replace(/_/g, " ")}</span>
                        </div>
                      ) : <span className="text-slate-400 text-xs">Unassigned</span>}
                    </td>
                    <td className="px-5 py-3 text-slate-600">
                      {t.due_at ?? "—"}
                      {t.status === "OVERDUE" && <div className="text-xs text-rose-600">Overdue</div>}
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex justify-end">
                        <Ring percent={matchByThread[t.thread_id] ?? 90} size={36} />
                      </div>
                    </td>
                  </tr>
                );
              })}
              {sortedThreads.length === 0 && (
                <tr><td colSpan={6} className="px-5 py-10 text-center text-slate-400">No threads yet. Ingest an artifact to get started.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 p-5">
            <div className="font-medium text-slate-800 mb-3">Why this matters</div>
            <ul className="space-y-2.5 text-sm text-slate-600">
              {[
                "Consolidates imaging, notes, labs, and messages across encounters.",
                "Finds relevant evidence scoped strictly to the individual patient.",
                "Every suggestion is linked to source documents and locations.",
                "Consequential actions stay under clinician review and approval.",
              ].map((line) => (
                <li key={line} className="flex gap-2.5">
                  <CheckCircle2 size={16} className="text-emerald-500 shrink-0 mt-0.5" />
                  {line}
                </li>
              ))}
            </ul>
          </div>
          <div className="bg-white rounded-2xl border border-slate-200 p-5">
            <div className="font-medium text-slate-800 mb-3">Recent activity</div>
            <ul className="text-sm text-slate-600 space-y-3">
              {sortedThreads.slice(0, 5).map((t) => (
                <li key={t.thread_id} className="flex items-center justify-between gap-2">
                  <span className="truncate">{t.title}</span>
                  <StatusBadge status={t.status} />
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatTile({ icon, label, value, tone }: { icon: React.ComponentType<{ size?: number }>; label: string; value: number; tone: "blue" | "amber" | "rose" | "teal" }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 flex items-center gap-4">
      <IconTile icon={icon as never} tone={tone} size={44} />
      <div>
        <div className="text-2xl font-semibold text-slate-900">{value}</div>
        <div className="text-xs text-slate-500">{label}</div>
      </div>
    </div>
  );
}
