import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Loader2, PlayCircle } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

export default function Benchmarks() {
  const [runs, setRuns] = useState([]);
  const [running, setRunning] = useState(false);

  const load = () => api.get("/benchmark").then((r) => setRuns(r.data));
  useEffect(() => { load(); }, []);

  const run = async () => {
    setRunning(true);
    try { await api.post("/benchmark"); await load(); }
    finally { setRunning(false); }
  };

  const latest = runs[0];
  const chartData = (latest?.results || []).map((r) => ({
    name: r.config.replace(" (Proposed)", "*"),
    evidence: r.avg_evidence,
    validation: r.avg_validation,
    cost: r.avg_cost * 1000, // scale for visibility
  }));

  return (
    <div className="flex-1 p-8 overflow-y-auto" data-testid="bench-root">
      <div className="flex items-start justify-between">
        <div>
          <div className="overline">Experiment</div>
          <h1 className="text-4xl sm:text-5xl tracking-tight mt-1">Benchmarks</h1>
          <p className="text-sm text-[#A1A1AA] mt-2 max-w-2xl">
            Ablation across six configurations on the same query battery.
            Compare vector-only vs OKF-hybrid, single-mode vs collaborative BOTH mode.
          </p>
        </div>
        <button
          onClick={run}
          disabled={running}
          className="k-btn k-btn-primary flex items-center gap-2"
          data-testid="run-bench-btn"
        >
          {running ? <Loader2 size={14} className="animate-spin" /> : <PlayCircle size={14} />}
          {running ? "Running…" : "Run Benchmark"}
        </button>
      </div>

      {latest && (
        <div className="mt-6 space-y-4 fade-up">
          <div className="k-card">
            <div className="overline mb-3">Latest Run · {latest.at?.slice(0, 19)}</div>
            <div className="h-72">
              <ResponsiveContainer>
                <BarChart data={chartData}>
                  <CartesianGrid stroke="#222" strokeDasharray="3 3" />
                  <XAxis dataKey="name" stroke="#71717A" tick={{ fontFamily: "IBM Plex Mono", fontSize: 10 }} interval={0} angle={-15} textAnchor="end" height={70} />
                  <YAxis stroke="#71717A" tick={{ fontFamily: "IBM Plex Mono", fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: "#141414", border: "1px solid #2A2A2A" }} />
                  <Legend wrapperStyle={{ fontFamily: "IBM Plex Mono", fontSize: 11 }} />
                  <Bar dataKey="evidence" fill="#0055FF" name="Evidence" />
                  <Bar dataKey="validation" fill="#34C759" name="Validation" />
                  <Bar dataKey="cost" fill="#FFCC00" name="Cost ×1000" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="k-card">
            <div className="overline mb-3">Detailed Results</div>
            <table className="w-full text-sm mono">
              <thead>
                <tr className="text-[#71717A] text-xs uppercase tracking-wider border-b border-[#2A2A2A]">
                  <th className="text-left py-2">config</th>
                  <th className="text-left py-2">mode</th>
                  <th className="text-right py-2">evidence</th>
                  <th className="text-right py-2">validation</th>
                  <th className="text-right py-2">cost</th>
                  <th className="text-right py-2">latency</th>
                  <th className="text-right py-2">failures</th>
                </tr>
              </thead>
              <tbody>
                {latest.results.map((r, i) => (
                  <tr key={i} className="border-b border-[#1A1A1A] row-hover">
                    <td className="py-3 text-white">{r.config}</td>
                    <td className="py-3 text-[#A1A1AA]">{r.mode}</td>
                    <td className="py-3 text-right text-[#0055FF]">{r.avg_evidence}</td>
                    <td className="py-3 text-right text-[#34C759]">{r.avg_validation}</td>
                    <td className="py-3 text-right text-[#FFCC00]">${r.avg_cost}</td>
                    <td className="py-3 text-right text-[#A1A1AA]">{r.avg_latency_ms} ms</td>
                    <td className="py-3 text-right">
                      <span className={r.validation_failures > 0 ? "text-[#FF3B30]" : "text-[#71717A]"}>
                        {r.validation_failures}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!latest && (
        <div className="mt-6 k-card text-sm text-[#71717A]">
          No benchmark runs yet. Click "Run Benchmark" to execute 5 queries across 6 configurations.
        </div>
      )}
    </div>
  );
}
