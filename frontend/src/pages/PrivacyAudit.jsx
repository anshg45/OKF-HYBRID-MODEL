import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { SensitivityPill } from "../components/PillBadge";

export default function PrivacyAudit() {
  const [data, setData] = useState({ events: [], total_events: 0 });
  useEffect(() => { api.get("/privacy/audit").then((r) => setData(r.data)); }, []);

  return (
    <div className="flex-1 p-8 overflow-y-auto" data-testid="privacy-root">
      <div className="overline">Compliance</div>
      <h1 className="text-4xl sm:text-5xl tracking-tight mt-1">Privacy Audit</h1>
      <p className="text-sm text-[#A1A1AA] mt-2 max-w-2xl">
        Every piece of information that crossed the local boundary is logged here
        with its transformation trail. This is an auditable privacy ledger.
      </p>

      <div className="mt-6 k-card">
        <div className="overline mb-3">
          Cross-Boundary Events <span className="text-white">{data.total_events}</span>
        </div>
        {data.events.length === 0 && (
          <div className="text-sm text-[#71717A]">No cloud releases yet.</div>
        )}
        <table className="w-full text-sm mono">
          <thead>
            <tr className="text-[#71717A] text-xs uppercase tracking-wider border-b border-[#2A2A2A]">
              <th className="text-left py-2">query</th>
              <th className="text-left py-2">node</th>
              <th className="text-left py-2">sensitivity</th>
              <th className="text-left py-2">transformations</th>
              <th className="text-left py-2">mode</th>
              <th className="text-left py-2">at</th>
            </tr>
          </thead>
          <tbody>
            {data.events.map((e, i) => (
              <tr key={i} className="border-b border-[#1A1A1A] row-hover" data-testid={`priv-event-${i}`}>
                <td className="py-3 text-[#A1A1AA]">{e.query_id}</td>
                <td className="py-3 text-white">{e.title}</td>
                <td className="py-3"><SensitivityPill level={e.sensitivity} /></td>
                <td className="py-3 text-[#FFCC00] text-xs">
                  {e.transformations.length === 0 ? (
                    <span className="text-[#71717A]">none</span>
                  ) : (
                    e.transformations.map((t) => `${t.type}:${t.entity}×${t.count}`).join(" · ")
                  )}
                </td>
                <td className="py-3 text-[#A1A1AA]">{e.mode}</td>
                <td className="py-3 text-[#71717A] text-xs">{e.started_at?.slice(11, 19)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
