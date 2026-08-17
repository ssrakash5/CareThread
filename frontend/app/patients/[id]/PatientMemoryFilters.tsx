"use client";

import { useRouter, usePathname } from "next/navigation";

export default function PatientMemoryFilters({ types, active }: { types: string[]; active?: string }) {
  const router = useRouter();
  const pathname = usePathname();

  function setFilter(t?: string) {
    router.push(t ? `${pathname}?type=${t}` : pathname);
  }

  return (
    <div className="flex flex-wrap gap-2">
      <Chip label="All" active={!active} onClick={() => setFilter()} />
      {types.map((t) => (
        <Chip key={t} label={t.replace(/_/g, " ")} active={active === t} onClick={() => setFilter(t)} />
      ))}
    </div>
  );
}

function Chip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`text-xs px-3 py-1.5 rounded-full border ${
        active ? "bg-teal-600 border-teal-600 text-white" : "bg-white border-slate-200 text-slate-600 hover:border-teal-300"
      }`}
    >
      {label}
    </button>
  );
}
