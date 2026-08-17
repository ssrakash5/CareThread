const STATUS_STYLES: Record<string, string> = {
  PROPOSED: "bg-slate-100 text-slate-700",
  OPEN: "bg-blue-100 text-blue-700",
  IN_PROGRESS: "bg-blue-100 text-blue-700",
  AWAITING_EVIDENCE: "bg-amber-100 text-amber-700",
  OVERDUE: "bg-red-100 text-red-700",
  ESCALATED: "bg-red-100 text-red-700",
  CLOSURE_PROPOSED: "bg-violet-100 text-violet-700",
  CLOSED: "bg-emerald-100 text-emerald-700",
  REJECTED: "bg-slate-200 text-slate-500",
  PENDING: "bg-amber-100 text-amber-700",
  APPROVED: "bg-emerald-100 text-emerald-700",
  EXPIRED: "bg-slate-200 text-slate-500",
};

export function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_STYLES[status] || "bg-slate-100 text-slate-700";
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

const PRIORITY_STYLES: Record<string, string> = {
  ROUTINE: "bg-slate-100 text-slate-600",
  URGENT: "bg-red-100 text-red-700",
};

export function PriorityBadge({ priority }: { priority: string }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${PRIORITY_STYLES[priority] || "bg-slate-100 text-slate-600"}`}>
      {priority}
    </span>
  );
}
