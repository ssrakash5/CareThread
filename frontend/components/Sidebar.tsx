"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Users, MessagesSquare, FileSearch, History, Settings, Link2, ChevronDown } from "lucide-react";
import Avatar from "./Avatar";

const links = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/patients", label: "Patients", icon: Users },
  { href: "/evidence", label: "Evidence", icon: FileSearch },
  { href: "/review", label: "Clinician Review", icon: MessagesSquare },
];

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-60 shrink-0 border-r border-slate-200 bg-white flex flex-col">
      <div className="h-16 px-5 flex items-center gap-2 border-b border-slate-200">
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-teal-600 text-white">
          <Link2 size={17} />
        </span>
        <span className="font-semibold text-slate-900 text-[15px]">CareThread</span>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {links.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                active ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              }`}
            >
              <Icon size={17} strokeWidth={2} />
              {label}
            </Link>
          );
        })}
        <div className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-300 cursor-default">
          <Settings size={17} />
          Settings
        </div>
      </nav>
      <div className="px-3 py-3 border-t border-slate-200 flex items-center gap-2.5">
        <Avatar name="Katherine Lee" size={32} />
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium text-slate-800 truncate">Katherine Lee, MD</div>
          <div className="text-xs text-slate-400 truncate">Care Coordinator</div>
        </div>
        <ChevronDown size={14} className="text-slate-400" />
      </div>
    </aside>
  );
}
