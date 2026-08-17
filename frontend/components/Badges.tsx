const STATUS_STYLES: Record<string, string> = {
  PROPOSED: "bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-200",
  OPEN: "bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-200",
  IN_PROGRESS: "bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-200",
  AWAITING_EVIDENCE: "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-200",
  OVERDUE: "bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-200",
  ESCALATED: "bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-200",
  CLOSURE_PROPOSED: "bg-violet-50 text-violet-700 ring-1 ring-inset ring-violet-200",
  CLOSED: "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-200",
  REJECTED: "bg-slate-100 text-slate-500 ring-1 ring-inset ring-slate-200",
  PENDING: "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-200",
  APPROVED: "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-200",
  EXPIRED: "bg-slate-100 text-slate-500 ring-1 ring-inset ring-slate-200",
};

export function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_STYLES[status] || "bg-slate-100 text-slate-600 ring-1 ring-inset ring-slate-200";
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ${cls}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

const PRIORITY_STYLES: Record<string, string> = {
  ROUTINE: "bg-slate-100 text-slate-600 ring-1 ring-inset ring-slate-200",
  URGENT: "bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-200",
};

export function PriorityBadge({ priority }: { priority: string }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${PRIORITY_STYLES[priority] || "bg-slate-100 text-slate-600 ring-1 ring-inset ring-slate-200"}`}>
      {priority}
    </span>
  );
}
