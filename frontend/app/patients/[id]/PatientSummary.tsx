"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Sparkles } from "lucide-react";

export default function PatientSummary({ patientId }: { patientId: string }) {
  const [summary, setSummary] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setSummary(null);
    api.getPatientSummary(patientId).then((r) => {
      setSummary(r.summary);
      setLoading(false);
    });
  }, [patientId]);

  return (
    <div className="flex items-start gap-1.5 text-sm text-slate-600 mt-1.5 max-w-2xl">
      <Sparkles size={14} className="text-blue-500 shrink-0 mt-0.5" />
      {loading ? (
        <span className="text-slate-400 italic">Summarizing…</span>
      ) : (
        <span>{summary}</span>
      )}
    </div>
  );
}
