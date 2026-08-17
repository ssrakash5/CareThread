import Link from "next/link";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { StatusBadge, PriorityBadge } from "@/components/Badges";
import IconTile, { toneForTitle } from "@/components/IconTile";
import Ring from "@/components/Ring";
import Avatar from "@/components/Avatar";
import ThreadActions from "./ThreadActions";
import { Stethoscope, History as HistoryIcon, FileText, UserPlus, ShieldCheck } from "lucide-react";

export const dynamic = "force-dynamic";

const EVENT_DOT_CLASS: Record<string, string> = {
  THREAD_OPENED: "bg-blue-500",
  THREAD_IN_PROGRESS: "bg-blue-500",
  OWNER_ASSIGNED: "bg-violet-500",
  EVIDENCE_LINKED: "bg-emerald-500",
  DEADLINE_EXTENDED: "bg-amber-500",
  ESCALATION_APPROVED: "bg-rose-500",
  CLOSURE_PROPOSED: "bg-violet-500",
  THREAD_CLOSED: "bg-emerald-500",
  THREAD_REJECTED: "bg-rose-500",
};
const DEFAULT_DOT_CLASS = "bg-slate-400";

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

  const tone = toneForTitle(thread.title);

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-3">
        <Link href="/" className="hover:text-teal-700">Threads</Link>
        <span>/</span>
        <Link href={`/patients/${patient.patient_id}`} className="hover:text-teal-700">{patient.display_name}</Link>
        <span>/</span>
        <span className="text-slate-500">{thread.title}</span>
      </div>

      <div className="grid grid-cols-3 gap-6 items-start">
        <div className="col-span-2 space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 p-6">
            <div className="flex items-start gap-4">
              <IconTile icon={Stethoscope} tone={tone} size={48} />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h1 className="text-lg font-semibold text-slate-900">{patient.display_name} — {thread.title}</h1>
                  <StatusBadge status={thread.status} />
                </div>
                <div className="text-sm text-slate-500 mt-1">
                  MRN {patient.mrn} · {thread.thread_type.replace(/_/g, " ")}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-5 gap-4 mt-6 pt-6 border-t border-slate-100 text-sm">
              <Field label="Owner">
                {thread.owner_user_id ? (
                  <div className="flex items-center gap-2 mt-1">
                    <Avatar name={thread.owner_user_id} size={22} />
                    <span className="text-slate-800">{thread.owner_user_id.replace(/_/g, " ")}</span>
                  </div>
                ) : <div className="text-slate-400 mt-1">Unassigned</div>}
              </Field>
              <Field label="Due date">
                <div className={`mt-1 ${thread.status === "OVERDUE" ? "text-rose-600 font-medium" : "text-slate-800"}`}>
                  {thread.due_at ?? "—"}
                </div>
              </Field>
              <Field label="Jurisdiction">
                <div className="text-slate-800 mt-1">{patient.jurisdiction}</div>
              </Field>
              <Field label="Priority">
                <div className="mt-1"><PriorityBadge priority={thread.priority} /></div>
              </Field>
              <Field label="Evidence">
                <div className="mt-0.5"><Ring percent={evidence.length ? 92 : 0} size={34} /></div>
              </Field>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-5">
              <div className="font-medium text-slate-800">Thread timeline</div>
              <Link href={`/threads/${id}/history`} className="text-xs text-teal-700 hover:underline flex items-center gap-1">
                <HistoryIcon size={13} /> Full history
              </Link>
            </div>
            <ol className="relative border-l border-slate-200 ml-3 space-y-6">
              {timeline.map((ev) => (
                <li key={ev.event_id} className="ml-6">
                  <span className={`absolute -left-[9px] flex h-4 w-4 items-center justify-center rounded-full ring-4 ring-white ${EVENT_DOT_CLASS[ev.event_type] ?? DEFAULT_DOT_CLASS}`} />
                  <div className="text-xs text-slate-400">{new Date(ev.created_at).toLocaleString()}</div>
                  <div className="font-medium text-slate-800 mt-0.5">{ev.event_type.replace(/_/g, " ")}</div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {ev.actor_type === "care_agent" ? "CareThread agent" : `${ev.actor_id.replace(/_/g, " ")}`}
                  </div>
                </li>
              ))}
              {timeline.length === 0 && <li className="ml-6 text-sm text-slate-400">No events yet.</li>}
            </ol>
          </div>
        </div>

        <div className="space-y-6">
          <ThreadActions thread={thread} />

          <div className="bg-white rounded-2xl border border-slate-200 p-5">
            <div className="font-medium text-slate-800 mb-3 flex items-center gap-2">
              <FileText size={15} className="text-slate-400" /> Evidence with citations
            </div>
            <ul className="space-y-3">
              {evidence.map((e) => (
                <li key={e.thread_evidence_id} className="text-sm border-l-2 border-teal-500 pl-3">
                  <div className="font-medium text-slate-800">{e.relationship_type.replace(/_/g, " ")}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{e.match_reason}</div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {(e.match_score * 100).toFixed(0)}% match · {e.approval_status}
                  </div>
                </li>
              ))}
              {evidence.length === 0 && <li className="text-sm text-slate-400">No linked evidence yet.</li>}
            </ul>
          </div>

          <div className="bg-blue-50/60 rounded-2xl border border-blue-100 p-5">
            <div className="font-medium text-slate-800 mb-2 flex items-center gap-2">
              <ShieldCheck size={15} className="text-blue-600" /> Why this thread exists
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              {thread.status === "REJECTED"
                ? "This thread was proposed by the agent and rejected by a clinician."
                : "A finding was identified with a documented follow-up recommendation. CareThread is tracking this obligation until a clinician confirms it's resolved."}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs text-slate-400 uppercase tracking-wide flex items-center gap-1">
        {label === "Owner" && <UserPlus size={11} />} {label}
      </div>
      {children}
    </div>
  );
}
