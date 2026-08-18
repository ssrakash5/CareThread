"use client";

import { useState } from "react";
import { api, artifactFileUrl } from "@/lib/api";
import type { Artifact, ArtifactDetail } from "@/lib/types";
import IconTile, { toneForArtifact } from "@/components/IconTile";
import { FileStack, ChevronDown, ChevronRight, FileText } from "lucide-react";

function ArtifactRow({ artifact }: { artifact: Artifact }) {
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState<ArtifactDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const isImage = artifact.artifact_type === "IMAGE";

  function toggle() {
    if (!open && !detail) {
      setLoading(true);
      api.getArtifact(artifact.artifact_id).then((d) => {
        setDetail(d);
        setLoading(false);
      });
    }
    setOpen((v) => !v);
  }

  return (
    <div>
      <button onClick={toggle} className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-slate-50">
        {isImage ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={artifactFileUrl(artifact.artifact_id)}
            alt={artifact.title}
            className="h-[34px] w-[34px] rounded-xl object-cover shrink-0 border border-slate-200"
          />
        ) : (
          <IconTile icon={FileStack} tone={toneForArtifact(artifact.artifact_type)} size={34} />
        )}
        <div className="flex-1 min-w-0">
          <div className="font-medium text-slate-800 text-sm truncate">{artifact.title}</div>
          <div className="text-xs text-slate-500 mt-0.5">
            {artifact.artifact_type.replace(/_/g, " ")} · {artifact.source_provider || "Unknown source"}
          </div>
        </div>
        <div className="text-xs text-slate-400 shrink-0">{artifact.document_date}</div>
        {open ? <ChevronDown size={14} className="text-slate-400 shrink-0" /> : <ChevronRight size={14} className="text-slate-400 shrink-0" />}
      </button>

      {open && (
        <div className="px-4 pb-4 pl-[3.25rem] space-y-3">
          {loading && <div className="text-xs text-slate-400">Loading…</div>}
          {detail && (
            <>
              {isImage && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={artifactFileUrl(artifact.artifact_id)}
                  alt={artifact.title}
                  className="max-w-xs rounded-lg border border-slate-200"
                />
              )}
              {detail.has_file && !isImage && (
                <a
                  href={artifactFileUrl(artifact.artifact_id)}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs text-teal-700 bg-teal-50 border border-teal-100 rounded-md px-2.5 py-1.5 hover:border-teal-300"
                >
                  <FileText size={13} /> Open original file
                </a>
              )}
              {detail.facts.length > 0 && (
                <div>
                  <div className="text-xs font-medium text-slate-500 mb-1.5">Extracted facts</div>
                  <ul className="space-y-1.5">
                    {detail.facts.map((f) => (
                      <li key={f.fact_id} className="text-xs text-slate-600 bg-slate-50 rounded-md px-2.5 py-1.5">
                        <span className="font-medium text-slate-700">{f.fact_type.replace(/_/g, " ")}</span>
                        {": "}{f.fact_text}
                        {f.normalized_value && <span className="text-slate-400"> ({f.normalized_value})</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {detail.chunks.length > 0 && (
                <div>
                  <div className="text-xs font-medium text-slate-500 mb-1.5">{isImage ? "Caption" : "Content"}</div>
                  <div className="text-xs text-slate-600 whitespace-pre-wrap bg-slate-50 rounded-md px-2.5 py-2 max-h-48 overflow-y-auto">
                    {detail.chunks.join("\n\n")}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function ArtifactList({ artifacts, activeType }: { artifacts: Artifact[]; activeType?: string }) {
  return (
    <div className="mt-3 bg-white rounded-2xl border border-slate-200 divide-y divide-slate-100">
      {artifacts.map((a) => (
        <ArtifactRow key={a.artifact_id} artifact={a} />
      ))}
      {artifacts.length === 0 && (
        <div className="p-8 text-center text-slate-400 text-sm">
          No artifacts{activeType ? ` of type ${activeType}` : ""} for this patient yet.
        </div>
      )}
    </div>
  );
}
