import Link from "next/link";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { StatusBadge, PriorityBadge } from "@/components/Badges";
import ThreadActions from "./ThreadActions";
import { History } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function ThreadDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let thread;
  try {
    thread = await api.getThread(id);
  } catch {
    notFound();
  }
  const [patient, timeline, evidence] = await Promise.all([
    api.getPatient(thread.patient_id),
    api.getTimeline(id),
    api.getEvidence(id),
  ]);

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">{thread.title}</h1>
            <div className="text-sm text-slate-500 mt-1">
              {patient.display_name} · MRN {patient.mrn}
            </div>
          </div>
          <div className="flex gap-2">
            <StatusBadge status={thread.status} />
            <PriorityBadge priority={thread.priority} />
          </div>
        </div>

        <div className="grid grid-cols-4 gap-4 mt-6 text-sm">
          <Field label="Thread type" value={thread.thread_type.replace(/_/g, " ")} />
          <Field label="Owner" value={thread.owner_user_id ?? "Unassigned"} />
          <Field label="Due date" value={thread.due_at ?? "—"} />
          <Field label="Jurisdiction" value={patient.jurisdiction} />
        </div>

        <ThreadActions thread={thread} />
      </div>

      <div className="grid grid-cols-2 gap-6 mt-6">
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="font-medium">Longitudinal timeline</div>
            <Link href={`/threads/${id}/history`} className="text-xs text-teal-700 hover:underline flex items-center gap-1">
              <History size={13} /> Full history
            </Link>
          </div>
          <ol className="space-y-4">
            {timeline.map((ev) => (
              <li key={ev.event_id} className="text-sm">
                <div className="font-medium text-slate-800">{ev.event_type.replace(/_/g, " ")}</div>
                <div className="text-slate-500 text-xs mt-0.5">
                  {new Date(ev.created_at).toLocaleString()} · {ev.actor_id}
                </div>
              </li>
            ))}
            {timeline.length === 0 && <li className="text-sm text-slate-400">No events yet.</li>}
          </ol>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <div className="font-medium mb-4">Evidence citations</div>
          <ul className="space-y-3">
            {evidence.map((e) => (
              <li key={e.thread_evidence_id} className="text-sm border-l-2 border-teal-500 pl-3">
                <div className="font-medium text-slate-800">{e.relationship_type.replace(/_/g, " ")}</div>
                <div className="text-slate-500 text-xs mt-0.5">{e.match_reason}</div>
                <div className="text-xs text-slate-400 mt-0.5">
                  Match confidence {(e.match_score * 100).toFixed(0)}% · {e.approval_status}
                </div>
              </li>
            ))}
            {evidence.length === 0 && <li className="text-sm text-slate-400">No linked evidence yet.</li>}
          </ul>
        </div>
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-slate-400 uppercase tracking-wide">{label}</div>
      <div className="text-slate-800 mt-0.5">{value}</div>
    </div>
  );
}
