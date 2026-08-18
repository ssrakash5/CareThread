"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { AlertTriangle } from "lucide-react";

export default function CheckOverdueButton() {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [result, setResult] = useState<string | null>(null);

  function run() {
    startTransition(async () => {
      setResult(null);
      const actions = await api.checkOverdue();
      setResult(actions.length ? `Flagged ${actions.length} overdue thread(s) for escalation.` : "No overdue threads found.");
      router.refresh();
    });
  }

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={run}
        disabled={pending}
        className="flex items-center gap-1.5 text-xs bg-white border border-slate-300 rounded-md px-3 py-1.5 hover:border-rose-300 disabled:opacity-40"
      >
        <AlertTriangle size={13} className="text-rose-500" />
        {pending ? "Checking…" : "Check overdue threads"}
      </button>
      {result && <span className="text-xs text-slate-500">{result}</span>}
    </div>
  );
}
