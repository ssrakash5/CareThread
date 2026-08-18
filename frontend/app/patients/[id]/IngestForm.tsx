"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

function isImageFile(file: File): boolean {
  return file.type.startsWith("image/") || /\.(png|jpe?g)$/i.test(file.name);
}

export default function IngestForm({ patientId, artifactTypes }: { patientId: string; artifactTypes: string[] }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [artifactType, setArtifactType] = useState(artifactTypes[0]);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [caption, setCaption] = useState("");
  const [documentDate, setDocumentDate] = useState(new Date().toISOString().slice(0, 10));
  const [result, setResult] = useState<string | null>(null);

  const fileIsImage = file ? isImageFile(file) : false;
  const canSubmit = file ? title && (!fileIsImage || caption) : title && text;

  function submit() {
    startTransition(async () => {
      setResult(null);
      const res = (file
        ? await api.uploadArtifact(patientId, {
            file, artifact_type: artifactType, title, document_date: documentDate, caption,
          })
        : await api.ingestArtifact(patientId, {
            artifact_type: artifactType, title, text, document_date: documentDate,
          })
      ) as { proposed_actions: { action_type: string }[]; match_candidates: unknown[] };
      const actionSummary = res.proposed_actions.map((a) => a.action_type).join(", ") || "no action proposed";
      setResult(`Ingested. Agent result: ${actionSummary}`);
      setTitle("");
      setText("");
      setFile(null);
      setCaption("");
      router.refresh();
    });
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5">
      <div className="space-y-3">
        <select value={artifactType} onChange={(e) => setArtifactType(e.target.value)} className="w-full border border-slate-300 rounded-md px-2.5 py-1.5 text-sm">
          {artifactTypes.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
        </select>
        <input placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} className="w-full border border-slate-300 rounded-md px-2.5 py-1.5 text-sm" />
        <input type="date" value={documentDate} onChange={(e) => setDocumentDate(e.target.value)} className="w-full border border-slate-300 rounded-md px-2.5 py-1.5 text-sm" />

        <input
          type="file"
          accept=".pdf,image/*,.txt"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="w-full border border-slate-300 rounded-md px-2.5 py-1.5 text-xs file:mr-2 file:rounded file:border-0 file:bg-slate-100 file:px-2 file:py-1"
        />
        {file && fileIsImage && (
          <input
            placeholder="Caption (required — images are stored as reference only, never auto-interpreted)"
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            className="w-full border border-slate-300 rounded-md px-2.5 py-1.5 text-sm"
          />
        )}
        {!file && (
          <textarea placeholder="Or paste document text" value={text} onChange={(e) => setText(e.target.value)} rows={8} className="w-full border border-slate-300 rounded-md px-2.5 py-1.5 text-sm font-mono" />
        )}

        <button
          disabled={pending || !canSubmit}
          onClick={submit}
          className="w-full rounded-md bg-teal-600 text-white text-sm px-3 py-2 hover:bg-teal-700 disabled:opacity-40"
        >
          {pending ? "Processing…" : file ? `Upload ${file.name}` : "Ingest artifact"}
        </button>
        {result && <div className="text-xs text-slate-600 bg-slate-50 rounded-md p-2">{result}</div>}
      </div>
    </div>
  );
}
