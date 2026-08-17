import { notFound } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/Badges";
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
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">{patient.display_name}</h1>
          <div className="text-sm text-slate-500 mt-1">MRN {patient.mrn} · DOB {patient.dob} · {patient.jurisdiction}</div>
        </div>
      </div>

      {threads.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {threads.map((t) => (
            <Link key={t.thread_id} href={`/threads/${t.thread_id}`} className="flex items-center gap-2 bg-white border border-slate-200 rounded-full pl-3 pr-2 py-1 text-xs hover:border-teal-300">
              {t.title} <StatusBadge status={t.status} />
            </Link>
          ))}
        </div>
      )}

      <div className="grid grid-cols-3 gap-6 mt-6">
        <div className="col-span-2">
          <PatientMemoryFilters types={ARTIFACT_TYPES} active={type} />
          <div className="mt-3 space-y-3">
            {artifacts.map((a) => (
              <div key={a.artifact_id} className="bg-white rounded-xl border border-slate-200 p-4">
                <div className="flex items-center justify-between">
                  <div className="font-medium text-slate-800">{a.title}</div>
                  <span className="text-xs text-slate-400">{a.document_date}</span>
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  {a.artifact_type.replace(/_/g, " ")} · {a.source_provider || "Unknown source"} · {a.status}
                </div>
              </div>
            ))}
            {artifacts.length === 0 && (
              <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-400 text-sm">
                No artifacts{type ? ` of type ${type}` : ""} for this patient yet.
              </div>
            )}
          </div>
        </div>

        <div>
          <IngestForm patientId={id} artifactTypes={ARTIFACT_TYPES} />
        </div>
      </div>
    </div>
  );
}
