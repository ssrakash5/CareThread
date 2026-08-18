import Link from "next/link";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/Badges";
import Avatar from "@/components/Avatar";
import IconTile, { toneForTitle } from "@/components/IconTile";
import { Stethoscope, ShieldCheck, CheckCircle2 } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function HistoryPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let thread;
  try {
    thread = await api.getThread(id);
  } catch {
    notFound();
  }
  const [events, patient] = await Promise.all([api.audit(id), api.getPatient(thread.patient_id)]);

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-3">
        <Link href={`/threads/${id}`} className="hover:text-teal-700">{"< Back to thread"}</Link>
      </div>
      <h1 className="text-xl font-semibold text-slate-900">History &amp; Provenance</h1>
      <p className="text-slate-500 text-sm mt-1">Complete history of this thread over time.</p>

      <div className="grid grid-cols-3 gap-6 mt-6 items-start">
        <div className="col-span-2 space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 p-5 flex items-center gap-4">
            <Avatar name={patient.display_name} size={40} />
            <div className="flex-1">
              <div className="font-semibold text-slate-900">{patient.display_name}</div>
              <div className="text-xs text-slate-500">MRN {patient.mrn}</div>
            </div>
            <IconTile icon={Stethoscope} tone={toneForTitle(thread.title)} size={36} />
            <div className="text-sm text-slate-700">{thread.title}</div>
            <StatusBadge status={thread.status} />
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 p-6">
            <div className="font-medium text-slate-800 mb-1">Audit Timeline</div>
            <div className="text-xs text-slate-400 mb-5">Chronological record of key events and changes.</div>
            <ol className="relative border-l border-slate-200 ml-3 space-y-6">
              {events.map((ev) => (
                <li key={ev.event_id} className="ml-6">
                  <span className="absolute -left-[7px] flex h-3.5 w-3.5 items-center justify-center rounded-full bg-teal-500 ring-4 ring-white" />
                  <div className="text-xs text-slate-400">
                    {new Date(ev.created_at).toLocaleDateString("en-US", { month: "short", day: "2-digit", year: "numeric" })}
                  </div>
                  <div className="font-medium text-slate-800 mt-0.5">{formatEvent(ev.event_type)}</div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {ev.actor_type === "care_agent" ? "CareThread agent" : `${ev.actor_id.replace(/_/g, " ")}`}
                    {ev.previous_state && ev.new_state && ev.previous_state !== ev.new_state && (
                      <span> · {ev.previous_state} → {ev.new_state}</span>
                    )}
                  </div>
                </li>
              ))}
              {events.length === 0 && <li className="ml-6 text-sm text-slate-400">No audit events recorded yet.</li>}
            </ol>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 p-5">
            <div className="font-medium text-slate-800 mb-3">Thread metadata</div>
            <dl className="space-y-3 text-sm">
              <Row label="Jurisdiction" value={patient.jurisdiction} />
              <Row label="Home region" value={patient.home_region} />
              <Row label="Owner" value={thread.owner_user_id?.replace(/_/g, " ") ?? "Unassigned"} />
              <Row label="Current status" value={<StatusBadge status={thread.status} />} />
              <Row label="Linked events" value={String(events.length)} />
            </dl>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 p-5">
            <div className="font-medium text-slate-800 mb-3 flex items-center gap-2">
              <ShieldCheck size={15} className="text-blue-600" /> What this screen shows
            </div>
            <ul className="space-y-2 text-sm text-slate-600">
              {["Complete history from creation to current state", "Evidence provenance, citation for each artifact", "Workflow state as it progressed over time"].map((l) => (
                <li key={l} className="flex gap-2"><CheckCircle2 size={15} className="text-emerald-500 shrink-0 mt-0.5" />{l}</li>
              ))}
            </ul>
          </div>

          <div className="bg-blue-50/60 rounded-2xl border border-blue-100 p-4 text-xs text-slate-600 leading-relaxed">
            Regional-by-row locality helps colocate patient memory with jurisdiction for performance — it does not, by
            itself, guarantee legal data residency. CareThread does not make regulatory or compliance promises.
          </div>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-slate-400">{label}</dt>
      <dd className="text-slate-800 font-medium">{value}</dd>
    </div>
  );
}

function formatEvent(eventType: string) {
  return eventType
    .toLowerCase()
    .split("_")
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");
}
