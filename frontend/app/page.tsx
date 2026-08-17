import Link from "next/link";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/Badges";
import { AlertTriangle, Clock, FileCheck2, Inbox } from "lucide-react";

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
  const needsReview = pendingActions.length;

  const today = new Date();
  const recentThreads = [...threads]
    .sort((a, b) => (b.opened_at || "").localeCompare(a.opened_at || ""))
    .slice(0, 8);

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
      <p className="text-slate-500 mt-1">Operational inbox for unresolved care obligations.</p>

      <div className="grid grid-cols-4 gap-4 mt-6">
        <StatTile icon={Inbox} label="Open Threads" value={openThreads.length} tone="blue" />
        <StatTile icon={FileCheck2} label="Needs Review" value={needsReview} tone="amber" />
        <StatTile icon={AlertTriangle} label="Overdue Follow-ups" value={overdue.length} tone="red" />
        <StatTile icon={Clock} label="Total Threads" value={threads.length} tone="slate" />
      </div>

      <div className="grid grid-cols-3 gap-6 mt-8">
        <div className="col-span-2 bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200 font-medium">CareThreads</div>
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wide">
              <tr>
                <th className="text-left px-5 py-2 font-medium">Patient</th>
                <th className="text-left px-5 py-2 font-medium">Finding</th>
                <th className="text-left px-5 py-2 font-medium">Status</th>
                <th className="text-left px-5 py-2 font-medium">Owner</th>
                <th className="text-left px-5 py-2 font-medium">Due date</th>
              </tr>
            </thead>
            <tbody>
              {recentThreads.map((t) => (
                <tr key={t.thread_id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-5 py-3">
                    <Link href={`/threads/${t.thread_id}`} className="font-medium text-teal-700 hover:underline">
                      {patientById[t.patient_id]?.display_name ?? t.patient_id}
                    </Link>
                  </td>
                  <td className="px-5 py-3 text-slate-700">{t.title}</td>
                  <td className="px-5 py-3"><StatusBadge status={t.status} /></td>
                  <td className="px-5 py-3 text-slate-600">{t.owner_user_id ?? "Unassigned"}</td>
                  <td className="px-5 py-3 text-slate-600">{t.due_at ?? "—"}</td>
                </tr>
              ))}
              {recentThreads.length === 0 && (
                <tr><td colSpan={5} className="px-5 py-8 text-center text-slate-400">No threads yet. Ingest an artifact to get started.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="font-medium mb-2">Why this matters</div>
            <p className="text-sm text-slate-600 leading-relaxed">
              CareThread keeps unresolved follow-up obligations alive after the encounter ends —
              linking later evidence back to the original finding until a clinician confirms
              closure, with full provenance at every step.
            </p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="font-medium mb-2">Recent activity</div>
            <ul className="text-sm text-slate-600 space-y-2">
              {threads.slice(0, 5).map((t) => (
                <li key={t.thread_id} className="flex justify-between gap-2">
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

function StatTile({ icon: Icon, label, value, tone }: { icon: typeof Inbox; label: string; value: number; tone: "blue" | "amber" | "red" | "slate" }) {
  const toneStyles: Record<string, string> = {
    blue: "bg-blue-50 text-blue-600",
    amber: "bg-amber-50 text-amber-600",
    red: "bg-red-50 text-red-600",
    slate: "bg-slate-100 text-slate-600",
  };
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 flex items-center gap-4">
      <div className={`rounded-lg p-2.5 ${toneStyles[tone]}`}>
        <Icon size={20} />
      </div>
      <div>
        <div className="text-2xl font-semibold text-slate-900">{value}</div>
        <div className="text-xs text-slate-500">{label}</div>
      </div>
    </div>
  );
}
