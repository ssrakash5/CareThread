import { api } from "@/lib/api";
import ReviewQueue from "./ReviewQueue";

export const dynamic = "force-dynamic";

export default async function ClinicianReviewPage() {
  const actions = await api.listActions("PENDING");
  const enriched = await Promise.all(
    actions.map(async (a) => {
      const thread = await api.getThread(a.thread_id);
      const patient = await api.getPatient(thread.patient_id);
      return { action: a, thread, patient };
    })
  );

  const counts = {
    closures: enriched.filter((e) => e.action.action_type === "CLOSE_THREAD").length,
    escalations: enriched.filter((e) => e.action.action_type === "ESCALATE_THREAD").length,
    extensions: enriched.filter((e) => e.action.action_type === "EXTEND_DUE_DATE").length,
    total: enriched.length,
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-semibold text-slate-900">Clinician Review</h1>
      <p className="text-slate-500 mt-1">Queue of proposed consequential actions awaiting approval.</p>

      <div className="grid grid-cols-4 gap-4 mt-6">
        <Metric label="Proposed Closures" value={counts.closures} />
        <Metric label="Proposed Escalations" value={counts.escalations} />
        <Metric label="Proposed Extensions" value={counts.extensions} />
        <Metric label="Awaiting Approval" value={counts.total} />
      </div>

      <ReviewQueue items={enriched} />
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="text-2xl font-semibold text-slate-900">{value}</div>
      <div className="text-xs text-slate-500 mt-1">{label}</div>
    </div>
  );
}
