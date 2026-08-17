import { Search, Bell, HelpCircle, Building2 } from "lucide-react";

export default function TopBar() {
  return (
    <header className="h-16 shrink-0 border-b border-slate-200 bg-white flex items-center gap-4 px-6">
      <div className="flex-1 max-w-md relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          readOnly
          placeholder="Search patients, threads, evidence…"
          className="w-full rounded-lg border border-slate-200 bg-slate-50 pl-9 pr-9 py-2 text-sm text-slate-500 placeholder:text-slate-400 focus:outline-none"
        />
        <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-slate-400 border border-slate-200 rounded px-1.5 py-0.5">/</kbd>
      </div>

      <div className="flex-1" />

      <button className="hidden sm:flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50">
        <Building2 size={15} className="text-slate-400" />
        Northwell Health (NY)
      </button>

      <button className="relative rounded-full p-2 hover:bg-slate-50 text-slate-500">
        <Bell size={18} />
        <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[10px] font-medium text-white">3</span>
      </button>
      <button className="rounded-full p-2 hover:bg-slate-50 text-slate-500">
        <HelpCircle size={18} />
      </button>
    </header>
  );
}
