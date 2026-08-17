import Link from "next/link";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function PatientsIndexPage() {
  const patients = await api.listPatients();
  return (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-semibold text-slate-900">Patient Memory</h1>
      <p className="text-slate-500 mt-1">Select a patient to view their longitudinal evidence repository.</p>
      <div className="mt-6 bg-white rounded-xl border border-slate-200 divide-y divide-slate-100">
        {patients.map((p) => (
          <Link key={p.patient_id} href={`/patients/${p.patient_id}`} className="flex items-center justify-between px-5 py-4 hover:bg-slate-50">
            <div>
              <div className="font-medium text-slate-800">{p.display_name}</div>
              <div className="text-xs text-slate-500 mt-0.5">MRN {p.mrn} · DOB {p.dob}</div>
            </div>
            <div className="text-xs text-slate-400">{p.jurisdiction}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
