import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { ModePill } from "../components/PillBadge";

export default function Traces() {
  const [list, setList] = useState([]);
  const [selected, setSelected] = useState(null);

  useEffect(() => { api.get("/traces").then((r) => setList(r.data)); }, []);
  const openTrace = async (id) => {
    const r = await api.get(`/traces/${id}`); setSelected(r.data);
  };

  return (
    <div className="flex-1 flex overflow-hidden" data-testid="traces-root">
      <div className="w-[520px] border-r border-[#2A2A2A] overflow-y-auto">
        <div className="p-6 border-b border-[#2A2A2A] sticky top-0 bg-[#0F0F0F] z-10">
          <div className="overline">Log</div>
          <h1 className="text-2xl tracking-tight mt-1">Execution Traces</h1>
        </div>
        {list.length === 0 && (
          <div className="p-6 text-sm text-[#71717A]">No traces yet — run a query.</div>
        )}
        {list.map((t) => (
          <button
            key={t.query_id}
            onClick={() => openTrace(t.query_id)}
            data-testid={`trace-item-${t.query_id}`}
            className={`w-full text-left p-4 border-b border-[#1A1A1A] row-hover ${
              selected?.query_id === t.query_id ? "bg-[#141414]" : ""
            }`}
          >
            <div className="flex justify-between items-start gap-3">
              <div className="text-sm text-white line-clamp-2 flex-1">{t.query}</div>
              <ModePill mode={t.execution_mode} />
            </div>
            <div className="mono text-[10px] text-[#71717A] mt-1 flex gap-3">
              <span>{t.query_id}</span>
              <span>${t.cost || 0}</span>
              <span>{t.latency_ms} ms</span>
              <span>conf {t.final_confidence || "—"}</span>
            </div>
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto p-8">
        {!selected && (
          <div className="text-sm text-[#71717A]">Select a trace to inspect.</div>
        )}
        {selected && (
          <div className="space-y-4 fade-up">
            <div>
              <div className="overline">Trace</div>
              <div className="text-lg mt-1">{selected.query}</div>
              <div className="mono text-[11px] text-[#71717A]">{selected.query_id}</div>
            </div>
            <div className="k-card">
              <div className="overline mb-2">Final Answer</div>
              <div className="whitespace-pre-wrap text-sm">{selected.final_answer}</div>
            </div>
            <div className="k-card">
              <div className="overline mb-2">Raw JSON</div>
              <pre className="mono text-[10px] leading-relaxed text-[#A1A1AA] whitespace-pre-wrap overflow-x-auto max-h-[600px]">
{JSON.stringify(selected, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
