import { api } from "@/lib/api";
import EvidenceReviewList from "./EvidenceReviewList";

export const dynamic = "force-dynamic";

export default async function EvidenceMatchReviewPage() {
  const actions = await api.listActions("PENDING");
  const linkActions = actions.filter((a) => a.action_type === "LINK_EVIDENCE");

  const enriched = await Promise.all(
    linkActions.map(async (a) => {
      const [thread, patient] = await Promise.all([
        api.getThread(a.thread_id),
        api.getThread(a.thread_id).then((t) => api.getPatient(t.patient_id)),
      ]);
      return { action: a, thread, patient };
    })
  );

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-semibold text-slate-900">Evidence Match Review</h1>
      <p className="text-slate-500 mt-1">
        How the agent matched new evidence to an existing CareThread — review before it&apos;s linked.
      </p>
      <EvidenceReviewList items={enriched} />
    </div>
  );
}
