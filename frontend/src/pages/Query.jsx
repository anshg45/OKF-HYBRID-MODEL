import { useState } from "react";
import { api } from "../lib/api";
import { SensitivityPill, ModePill } from "../components/PillBadge";
import { Zap, Loader2 } from "lucide-react";

const MODES = [
  { key: "auto", label: "AUTO" },
  { key: "local", label: "LOCAL" },
  { key: "cloud", label: "CLOUD" },
  { key: "both", label: "BOTH" },
];

const EXAMPLES = [
  "What is the Open Knowledge Format?",
  "Compare our company compensation with current industry trends.",
  "How does RAG reduce hallucination?",
  "What is our employee compensation policy?",
];

function Meter({ value, label }) {
  const pct = Math.max(0, Math.min(1, value || 0)) * 100;
  return (
    <div>
      <div className="flex justify-between text-[10px] uppercase tracking-wider text-[#71717A]">
        <span>{label}</span><span>{pct.toFixed(0)}%</span>
      </div>
      <div className="h-1.5 bg-[#1A1A1A] mt-1">
        <div className="h-full bg-[#0055FF]" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function Query() {
  const [q, setQ] = useState("Compare our company compensation with current industry trends.");
  const [mode, setMode] = useState("auto");
  const [loading, setLoading] = useState(false);
  const [trace, setTrace] = useState(null);

  const run = async () => {
    if (!q.trim()) return;
    setLoading(true);
    setTrace(null);
    try {
      const r = await api.post("/query", { query: q, mode });
      setTrace(r.data);
    } catch (e) {
      setTrace({ error: String(e) });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden" data-testid="query-root">
      <div className="flex-1 p-8 overflow-y-auto">
        <div className="overline">Ask</div>
        <h1 className="text-4xl sm:text-5xl tracking-tight mt-1">Query</h1>

        <div className="mt-6 k-card">
          <textarea
            className="k-textarea"
            rows={3}
            value={q}
            data-testid="query-input"
            onChange={(e) => setQ(e.target.value)}
            placeholder="Ask something…"
          />
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="overline mr-2">Execution</span>
            {MODES.map((m) => (
              <button
                key={m.key}
                data-testid={`mode-${m.key}`}
                onClick={() => setMode(m.key)}
                className={`k-btn ${mode === m.key ? "k-btn-primary" : ""}`}
              >
                {m.label}
              </button>
            ))}
            <div className="flex-1" />
            <button
              onClick={run}
              disabled={loading}
              className="k-btn k-btn-primary flex items-center gap-2"
              data-testid="run-query-btn"
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
              {loading ? "Executing" : "Execute"}
            </button>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                className="mono text-[#71717A] hover:text-white border border-[#2A2A2A] px-2 py-1"
                onClick={() => setQ(ex)}
                data-testid={`example-${ex.slice(0, 10)}`}
              >
                {ex}
              </button>
            ))}
          </div>
        </div>

        {loading && (
          <div className="mt-6 k-card mono text-xs text-[#A1A1AA] space-y-1">
            <div>› classifying query…</div>
            <div>› running adaptive retrieval (vector + OKF traversal)…</div>
            <div>› scoring evidence…</div>
            <div>› deciding execution mode…</div>
            <div>› calling local / cloud LLM…</div>
            <div>› validating response…</div>
          </div>
        )}

        {trace && !trace.error && (
          <div className="mt-6 space-y-4 fade-up">
            <div className="k-card">
              <div className="flex items-center justify-between mb-2">
                <div className="overline">Final Answer</div>
                <div className="flex gap-2">
                  <ModePill mode={trace.execution_mode} />
                  <span className="pill pill-blue">
                    conf {trace.final_confidence}
                  </span>
                  <span className={`pill ${trace.validation?.passed ? "pill-green" : "pill-red"}`}>
                    {trace.validation?.passed ? "validated" : "flagged"}
                  </span>
                </div>
              </div>
              <div className="whitespace-pre-wrap text-sm leading-relaxed" data-testid="answer-text">
                {trace.final_answer}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="k-card md:col-span-2">
                <div className="overline mb-3">Routing Decision</div>
                <div className="mono text-xs text-[#A1A1AA] space-y-1">
                  <div>mode: <span className="text-white">{trace.execution_mode}</span></div>
                  <div>complexity: {trace.complexity}</div>
                  <div>retrieval strategy: {trace.retrieval_strategy}</div>
                  <div className="text-[#71717A] mt-2">reasons:</div>
                  {(trace.routing?.reasons || []).map((r, i) => (
                    <div key={i}>· {r}</div>
                  ))}
                  <div className="mt-2">
                    <span className="text-[#71717A]">privacy exposure:</span>{" "}
                    <span className={trace.routing?.estimated_privacy_exposure > 0.5 ? "text-[#FF3B30]" : "text-[#34C759]"}>
                      {trace.routing?.estimated_privacy_exposure}
                    </span>
                  </div>
                </div>
              </div>

              <div className="k-card">
                <div className="overline mb-3">Evidence Quality</div>
                <div className="space-y-3">
                  <Meter value={trace.evidence_quality?.score} label="overall" />
                  <Meter value={trace.evidence_quality?.relevance} label="relevance" />
                  <Meter value={trace.evidence_quality?.authority} label="authority" />
                  <Meter value={trace.evidence_quality?.completeness} label="completeness" />
                  <Meter value={trace.evidence_quality?.diversity} label="diversity" />
                </div>
              </div>
            </div>

            <div className="k-card">
              <div className="overline mb-3">Retrieved Sources</div>
              <div className="space-y-2">
                {(trace.sources_used || []).map((s, i) => (
                  <div key={i} className="border border-[#2A2A2A] p-3 flex items-start justify-between gap-4">
                    <div>
                      <div className="text-sm">[{s.source_index}] {s.title}</div>
                      <div className="mono text-[11px] text-[#71717A] mt-1">
                        id={s.node_id} · method={s.method} · score={s.score?.toFixed(3)}
                      </div>
                      {s.sanitized && s.transformations?.length > 0 && (
                        <div className="mono text-[11px] text-[#FFCC00] mt-1">
                          sanitized before cloud: {s.transformations.map((t) => `${t.type}:${t.entity}×${t.count}`).join(" · ")}
                        </div>
                      )}
                    </div>
                    <div className="flex flex-col gap-1 items-end">
                      <SensitivityPill level={s.sensitivity} />
                      <span className={`pill ${s.cloud_allowed ? "pill-green" : "pill-red"}`}>
                        {s.cloud_allowed ? "cloud ok" : "local only"}
                      </span>
                    </div>
                  </div>
                ))}
                {(!trace.sources_used || trace.sources_used.length === 0) && (
                  <div className="text-xs text-[#71717A]">no sources retrieved</div>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="k-card">
                <div className="overline mb-3">Validation Checks</div>
                <div className="space-y-2">
                  {(trace.validation?.checks || []).map((c, i) => (
                    <div key={i} className="flex justify-between text-xs mono">
                      <span className={c.passed ? "text-[#A1A1AA]" : "text-[#FF3B30]"}>
                        {c.passed ? "✓" : "✗"} {c.name}
                      </span>
                      <span className="text-[#71717A]">{c.score}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="k-card">
                <div className="overline mb-3">Cost & Tokens</div>
                <div className="mono text-xs text-[#A1A1AA] space-y-1">
                  <div>cost: <span className="text-white">${trace.cost}</span></div>
                  <div>tokens in / out: {trace.tokens?.in} / {trace.tokens?.out}</div>
                  <div>latency: {trace.latency_ms} ms</div>
                  {trace.local_execution && (
                    <div className="text-[#71717A]">local model: <span className="text-[#34C759]">{trace.local_execution.model}</span></div>
                  )}
                  {trace.cloud_execution && (
                    <div className="text-[#71717A]">cloud model: <span className="text-[#0055FF]">{trace.cloud_execution.model}</span></div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {trace?.error && (
          <div className="mt-6 k-card border-[#FF3B30] text-[#FF3B30] mono text-xs">
            {trace.error}
          </div>
        )}
      </div>
    </div>
  );
}
