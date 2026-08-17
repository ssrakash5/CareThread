import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/Badges";

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
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">History &amp; Provenance</h1>
          <div className="text-sm text-slate-500 mt-1">{thread.title} · {patient.display_name}</div>
        </div>
        <StatusBadge status={thread.status} />
      </div>

      <div className="mt-6 bg-white rounded-xl border border-slate-200 p-6">
        <ol className="relative border-l border-slate-200 ml-2 space-y-6">
          {events.map((ev) => (
            <li key={ev.event_id} className="ml-6">
              <span className="absolute -left-[7px] flex h-3.5 w-3.5 items-center justify-center rounded-full bg-teal-500 ring-4 ring-white" />
              <div className="text-xs text-slate-400">
                {new Date(ev.created_at).toLocaleDateString(undefined, { month: "short", day: "2-digit", year: "numeric" })}
              </div>
              <div className="font-medium text-slate-800 mt-0.5">{formatEvent(ev.event_type)}</div>
              <div className="text-xs text-slate-500 mt-0.5">
                {ev.actor_type === "care_agent" ? "CareThread agent" : `Clinician (${ev.actor_id})`}
                {ev.previous_state && ev.new_state && ev.previous_state !== ev.new_state && (
                  <span> · {ev.previous_state} → {ev.new_state}</span>
                )}
              </div>
              {ev.event_metadata && Object.keys(ev.event_metadata).length > 0 && (
                <pre className="text-xs bg-slate-50 rounded-md mt-2 p-2 text-slate-500 overflow-x-auto">
                  {JSON.stringify(ev.event_metadata, null, 2)}
                </pre>
              )}
            </li>
          ))}
          {events.length === 0 && <li className="ml-6 text-sm text-slate-400">No audit events recorded yet.</li>}
        </ol>
      </div>
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
