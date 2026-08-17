import { notFound } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/Badges";
import Avatar from "@/components/Avatar";
import IconTile, { toneForArtifact } from "@/components/IconTile";
import { Info, Sparkles, FileStack, MapPin, History as HistoryIcon } from "lucide-react";
import IngestForm from "./IngestForm";
import PatientMemoryFilters from "./PatientMemoryFilters";

export const dynamic = "force-dynamic";

const ARTIFACT_TYPES = [
  "RADIOLOGY_REPORT", "DISCHARGE_SUMMARY", "PROGRESS_NOTE", "LAB_RESULT",
  "PATIENT_MESSAGE", "IMAGE", "SCHEDULING_NOTE",
];

export default async function PatientMemoryPage({
  params, searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ type?: string }>;
}) {
  const { id } = await params;
  const { type } = await searchParams;
  let patient;
  try {
    patient = await api.getPatient(id);
  } catch {
    notFound();
  }
  const [artifacts, threads] = await Promise.all([
    api.getPatientMemory(id, type),
    api.getPatientThreads(id),
  ]);

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-xl font-semibold text-slate-900">Patient Memory</h1>
      <p className="text-slate-500 text-sm mt-1">Longitudinal evidence repository for this patient.</p>

      <div className="bg-white rounded-2xl border border-slate-200 p-5 mt-5 flex items-center gap-4">
        <Avatar name={patient.display_name} size={44} />
        <div className="flex-1">
          <div className="font-semibold text-slate-900">{patient.display_name}</div>
          <div className="text-xs text-slate-500 mt-0.5">
            MRN {patient.mrn} · DOB {patient.dob} · {patient.jurisdiction}
          </div>
        </div>
        {threads.length > 0 && (
          <div className="hidden md:flex flex-wrap gap-2 max-w-md justify-end">
            {threads.map((t) => (
              <Link key={t.thread_id} href={`/threads/${t.thread_id}`} className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-full pl-3 pr-2 py-1 text-xs hover:border-teal-300">
                {t.title} <StatusBadge status={t.status} />
              </Link>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-3 gap-6 mt-6 items-start">
        <div className="col-span-2">
          <PatientMemoryFilters types={ARTIFACT_TYPES} active={type} />
          <div className="mt-3 bg-white rounded-2xl border border-slate-200 divide-y divide-slate-100">
            {artifacts.map((a) => (
              <div key={a.artifact_id} className="flex items-center gap-3 px-4 py-3">
                <IconTile icon={FileStack} tone={toneForArtifact(a.artifact_type)} size={34} />
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-slate-800 text-sm truncate">{a.title}</div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {a.artifact_type.replace(/_/g, " ")} · {a.source_provider || "Unknown source"}
                  </div>
                </div>
                <div className="text-xs text-slate-400 shrink-0">{a.document_date}</div>
              </div>
            ))}
            {artifacts.length === 0 && (
              <div className="p-8 text-center text-slate-400 text-sm">
                No artifacts{type ? ` of type ${type}` : ""} for this patient yet.
              </div>
            )}
          </div>

          <div className="mt-6">
            <div className="font-medium text-slate-800 mb-3 text-sm">Ingest new artifact</div>
            <IngestForm patientId={id} artifactTypes={ARTIFACT_TYPES} />
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 p-5">
            <div className="font-medium text-slate-800 mb-3 flex items-center gap-2">
              <Sparkles size={15} className="text-blue-600" /> Memory highlights
            </div>
            <ul className="text-sm text-slate-600 space-y-2">
              <li className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-blue-500" /> {artifacts.length} artifacts on file
              </li>
              <li className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-500" /> {threads.filter(t => !["CLOSED","REJECTED"].includes(t.status)).length} open thread(s)
              </li>
              <li className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> {threads.filter(t => t.status === "CLOSED").length} closed thread(s)
              </li>
            </ul>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 p-5">
            <div className="font-medium text-slate-800 mb-3 flex items-center gap-2">
              <MapPin size={15} className="text-slate-400" /> Key features
            </div>
            <ul className="space-y-2.5 text-sm text-slate-600">
              <li className="flex gap-2"><HistoryIcon size={14} className="text-slate-400 shrink-0 mt-0.5" /> Multimodal consolidation across reports, notes, labs, messages.</li>
              <li className="flex gap-2"><HistoryIcon size={14} className="text-slate-400 shrink-0 mt-0.5" /> Patient-scoped retrieval — never a cross-patient search.</li>
              <li className="flex gap-2"><HistoryIcon size={14} className="text-slate-400 shrink-0 mt-0.5" /> Every artifact is linked to its source and date.</li>
            </ul>
          </div>

          <div className="bg-blue-50/60 rounded-2xl border border-blue-100 p-4 flex gap-2.5">
            <Info size={15} className="text-blue-600 shrink-0 mt-0.5" />
            <p className="text-xs text-slate-600 leading-relaxed">
              CareThread&apos;s Patient Memory powers evidence matching and care coordination. It is not a diagnostic system.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
