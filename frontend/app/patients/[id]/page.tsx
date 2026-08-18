import { notFound } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/Badges";
import Avatar from "@/components/Avatar";
import { Info, Sparkles, MapPin, History as HistoryIcon, Users, MessageCircleQuestion } from "lucide-react";
import IngestForm from "./IngestForm";
import PatientMemoryFilters from "./PatientMemoryFilters";
import FamilyChat from "./FamilyChat";
import PatientChat from "./PatientChat";
import ArtifactList from "./ArtifactList";
import PatientSummary from "./PatientSummary";

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
  const family = await api.getPatientFamily(id).catch(() => null);
  const heredityThread = family
    ? threads.find((t) => t.thread_type === "HEREDITARY_RISK_REVIEW")
    : undefined;

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-xl font-semibold text-slate-900">Patient Memory</h1>
      <p className="text-slate-500 text-sm mt-1">Longitudinal evidence repository for this patient.</p>

      <div className="bg-white rounded-2xl border border-slate-200 p-5 mt-5 flex items-start gap-4">
        <Avatar name={patient.display_name} size={44} />
        <div className="flex-1">
          <div className="font-semibold text-slate-900">{patient.display_name}</div>
          <div className="text-xs text-slate-500 mt-0.5">
            MRN {patient.mrn} · DOB {patient.dob} · {patient.jurisdiction}
          </div>
          <PatientSummary patientId={id} />
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
          <ArtifactList artifacts={artifacts} activeType={type} />

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
            <div className="font-medium text-slate-800 flex items-center gap-2">
              <MessageCircleQuestion size={15} className="text-teal-600" /> Ask about this patient
            </div>
            <PatientChat patientId={id} />
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

          {family && (
            <div className="bg-white rounded-2xl border border-slate-200 p-5">
              <div className="font-medium text-slate-800 mb-3 flex items-center gap-2">
                <Users size={15} className="text-purple-600" /> Family
              </div>
              <ul className="text-sm text-slate-600 space-y-2">
                {family.members
                  .filter((m) => m.patient_id !== id)
                  .map((m) => {
                    const rel = family.relationships.find(
                      (r) => r.patient_id === id && r.related_patient_id === m.patient_id
                    );
                    return (
                      <li key={m.patient_id} className="flex items-center justify-between gap-2">
                        <Link href={`/patients/${m.patient_id}`} className="hover:text-teal-600 truncate">
                          {m.display_name}
                        </Link>
                        {rel && (
                          <span className="text-xs text-slate-400 shrink-0">
                            {rel.relationship_type.replace(/_/g, " ").toLowerCase()}
                          </span>
                        )}
                      </li>
                    );
                  })}
                {family.members.length <= 1 && (
                  <li className="text-slate-400 text-xs">No other members recorded.</li>
                )}
              </ul>
              {heredityThread && (
                <Link
                  href={`/threads/${heredityThread.thread_id}`}
                  className="mt-3 flex items-center gap-2 bg-purple-50 border border-purple-100 rounded-lg px-3 py-2 text-xs text-purple-700 hover:border-purple-300"
                >
                  Hereditary risk review flagged <StatusBadge status={heredityThread.status} />
                </Link>
              )}
              <FamilyChat familyId={family.family_id} />
            </div>
          )}

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
