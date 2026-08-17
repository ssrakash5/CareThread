"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, GitMerge, FolderClock, ClipboardCheck, History, Activity } from "lucide-react";

const links = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/evidence", label: "Evidence Match Review", icon: GitMerge },
  { href: "/patients", label: "Patient Memory", icon: FolderClock },
  { href: "/review", label: "Clinician Review", icon: ClipboardCheck },
];

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-64 shrink-0 border-r border-slate-200 bg-white flex flex-col">
      <div className="px-5 py-5 border-b border-slate-200 flex items-center gap-2">
        <Activity className="text-teal-600" size={22} />
        <div>
          <div className="font-semibold text-slate-900 leading-tight">CareThread</div>
          <div className="text-xs text-slate-500 leading-tight">Care continuity agent</div>
        </div>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {links.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                active ? "bg-teal-50 text-teal-700" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              }`}
            >
              <Icon size={17} />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="px-5 py-4 border-t border-slate-200 text-xs text-slate-400">
        Demo user: Dr. Kapoor · Clinician
      </div>
    </aside>
  );
}
