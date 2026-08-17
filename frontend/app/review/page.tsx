import { api } from "@/lib/api";
import IconTile from "@/components/IconTile";
import { Lock, TrendingUp, CalendarClock, Clock3, Info } from "lucide-react";
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
    <div className="p-8 max-w-7xl mx-auto">
      <h1 className="text-xl font-semibold text-slate-900">Review Proposed Actions</h1>
      <p className="text-slate-500 text-sm mt-1">CareThread ensures consequential actions are reviewed and approved by a clinician.</p>

      <div className="mt-5 flex items-start gap-2.5 bg-blue-50/60 border border-blue-100 rounded-2xl px-4 py-3">
        <Info size={16} className="text-blue-600 shrink-0 mt-0.5" />
        <p className="text-xs text-slate-600">
          Clinician approval is required for all consequential actions. These actions may close threads, escalate care, or extend deadlines.
        </p>
      </div>

      <div className="grid grid-cols-4 gap-4 mt-5">
        <Metric icon={Lock} tone="rose" label="Proposed Closures" value={counts.closures} />
        <Metric icon={TrendingUp} tone="amber" label="Proposed Escalations" value={counts.escalations} />
        <Metric icon={CalendarClock} tone="blue" label="Proposed Extensions" value={counts.extensions} />
        <Metric icon={Clock3} tone="teal" label="Awaiting Approval" value={counts.total} />
      </div>

      <ReviewQueue items={enriched} />
    </div>
  );
}

function Metric({ icon, tone, label, value }: { icon: React.ComponentType<{ size?: number }>; tone: "rose" | "amber" | "blue" | "teal"; label: string; value: number }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 flex items-center gap-4">
      <IconTile icon={icon as never} tone={tone} size={40} />
      <div>
        <div className="text-2xl font-semibold text-slate-900">{value}</div>
        <div className="text-xs text-slate-500">{label}</div>
      </div>
    </div>
  );
}
