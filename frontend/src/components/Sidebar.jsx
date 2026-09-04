import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Database, Search, Activity, Shield, FlaskConical, Network,
} from "lucide-react";

const items = [
  { to: "/", label: "Overview", icon: LayoutDashboard, tid: "nav-overview" },
  { to: "/knowledge", label: "Knowledge", icon: Database, tid: "nav-knowledge" },
  { to: "/query", label: "Query", icon: Search, tid: "nav-query" },
  { to: "/traces", label: "Traces", icon: Activity, tid: "nav-traces" },
  { to: "/privacy", label: "Privacy Audit", icon: Shield, tid: "nav-privacy" },
  { to: "/benchmarks", label: "Benchmarks", icon: FlaskConical, tid: "nav-benchmarks" },
];

export default function Sidebar() {
  return (
    <aside
      data-testid="sidebar"
      className="w-60 shrink-0 border-r border-[#2A2A2A] bg-[#0F0F0F] flex flex-col"
    >
      <div className="px-5 py-6 border-b border-[#2A2A2A]">
        <div className="flex items-center gap-2">
          <Network size={18} className="text-[#0055FF]" strokeWidth={1.5} />
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-[#71717A]">System</div>
            <div className="text-sm font-semibold tracking-tight">OKF Hybrid RAG</div>
          </div>
        </div>
      </div>
      <nav className="flex-1 py-4">
        {items.map((it) => {
          const Icon = it.icon;
          return (
            <NavLink
              key={it.to}
              to={it.to}
              end={it.to === "/"}
              data-testid={it.tid}
              className={({ isActive }) =>
                `flex items-center gap-3 px-5 py-2.5 text-sm border-l-2 transition-colors ${
                  isActive
                    ? "border-[#0055FF] bg-[#141414] text-white"
                    : "border-transparent text-[#A1A1AA] hover:text-white hover:bg-[#141414]"
                }`
              }
            >
              <Icon size={16} strokeWidth={1.5} />
              <span>{it.label}</span>
            </NavLink>
          );
        })}
      </nav>
      <div className="p-4 border-t border-[#2A2A2A] text-[10px] text-[#71717A] mono">
        <div>research prototype · v0.1</div>
        <div className="mt-1 flex items-center gap-2">
          <span className="pulse-dot inline-block w-1.5 h-1.5 bg-[#34C759] rounded-full" />
          <span>local · cloud · both</span>
        </div>
      </div>
    </aside>
  );
}
