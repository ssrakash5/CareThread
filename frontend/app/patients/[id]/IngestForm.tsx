"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function IngestForm({ patientId, artifactTypes }: { patientId: string; artifactTypes: string[] }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [artifactType, setArtifactType] = useState(artifactTypes[0]);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [documentDate, setDocumentDate] = useState(new Date().toISOString().slice(0, 10));
  const [result, setResult] = useState<string | null>(null);

  function submit() {
    startTransition(async () => {
      setResult(null);
      const res = await api.ingestArtifact(patientId, {
        artifact_type: artifactType, title, text, document_date: documentDate,
      }) as { proposed_actions: { action_type: string }[]; match_candidates: unknown[] };
      const actionSummary = res.proposed_actions.map((a) => a.action_type).join(", ") || "no action proposed";
      setResult(`Ingested. Agent result: ${actionSummary}`);
      setTitle("");
      setText("");
      router.refresh();
    });
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 sticky top-6">
      <div className="font-medium mb-3">Ingest new artifact</div>
      <div className="space-y-3">
        <select value={artifactType} onChange={(e) => setArtifactType(e.target.value)} className="w-full border border-slate-300 rounded-md px-2.5 py-1.5 text-sm">
          {artifactTypes.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
        </select>
        <input placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} className="w-full border border-slate-300 rounded-md px-2.5 py-1.5 text-sm" />
        <input type="date" value={documentDate} onChange={(e) => setDocumentDate(e.target.value)} className="w-full border border-slate-300 rounded-md px-2.5 py-1.5 text-sm" />
        <textarea placeholder="Document text" value={text} onChange={(e) => setText(e.target.value)} rows={8} className="w-full border border-slate-300 rounded-md px-2.5 py-1.5 text-sm font-mono" />
        <button
          disabled={pending || !title || !text}
          onClick={submit}
          className="w-full rounded-md bg-teal-600 text-white text-sm px-3 py-2 hover:bg-teal-700 disabled:opacity-40"
        >
          {pending ? "Processing…" : "Ingest artifact"}
        </button>
        {result && <div className="text-xs text-slate-600 bg-slate-50 rounded-md p-2">{result}</div>}
      </div>
    </div>
  );
}
