import { useEffect, useState } from "react";
import { api } from "../lib/api";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line,
} from "recharts";

function Kpi({ label, value, sub, testid }) {
  return (
    <div className="k-card fade-up" data-testid={testid}>
      <div className="overline">{label}</div>
      <div className="mt-2 text-3xl font-mono tracking-tight">{value}</div>
      {sub && <div className="text-xs text-[#71717A] mt-1 font-mono">{sub}</div>}
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.get("/stats").then((r) => setStats(r.data));
    api.get("/health").then((r) => setHealth(r.data));
  }, []);

  const modes = stats?.by_mode || {};
  const modeBars = ["local", "cloud", "both", "none"].map((m) => ({
    mode: m, count: modes[m] || 0,
  }));
  const costTrend = (stats?.recent_costs || []).map((c, i) => ({
    idx: i + 1, cost: c.cost, latency: c.latency,
  }));

  return (
    <div className="p-8 space-y-6" data-testid="dashboard-root">
      <div>
        <div className="overline">Command Center</div>
        <h1 className="text-4xl sm:text-5xl tracking-tight mt-1">Overview</h1>
        <p className="text-sm text-[#A1A1AA] mt-2 max-w-2xl">
          Real-time posture of the hybrid retrieval, routing, and privacy pipeline.
          Every query is a research-grade trace: what was retrieved, what left the
          local perimeter, and why.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Kpi
          label="Total Queries"
          value={stats?.total_queries ?? "—"}
          testid="kpi-total-queries"
        />
        <Kpi
          label="Total Cost (USD)"
          value={stats ? `$${stats.total_cost}` : "—"}
          sub={`avg confidence ${stats?.avg_confidence ?? "—"}`}
          testid="kpi-total-cost"
        />
        <Kpi
          label="Avg Latency"
          value={stats ? `${stats.avg_latency_ms} ms` : "—"}
          sub={`evidence ${stats?.avg_evidence ?? "—"}`}
          testid="kpi-latency"
        />
        <Kpi
          label="Knowledge Nodes"
          value={health?.nodes ?? "—"}
          sub={health?.llm_key_configured ? "LLM key ✓" : "LLM key ✗"}
          testid="kpi-nodes"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="k-card" data-testid="chart-modes">
          <div className="overline">Execution Mode Distribution</div>
          <div className="h-56 mt-3">
            <ResponsiveContainer>
              <BarChart data={modeBars}>
                <CartesianGrid stroke="#222" strokeDasharray="3 3" />
                <XAxis dataKey="mode" stroke="#71717A" tick={{ fontFamily: "IBM Plex Mono" }} />
                <YAxis stroke="#71717A" allowDecimals={false} tick={{ fontFamily: "IBM Plex Mono" }} />
                <Tooltip contentStyle={{ background: "#141414", border: "1px solid #2A2A2A" }} />
                <Bar dataKey="count" fill="#0055FF" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="k-card" data-testid="chart-cost">
          <div className="overline">Recent Cost & Latency Trend</div>
          <div className="h-56 mt-3">
            <ResponsiveContainer>
              <LineChart data={costTrend}>
                <CartesianGrid stroke="#222" strokeDasharray="3 3" />
                <XAxis dataKey="idx" stroke="#71717A" tick={{ fontFamily: "IBM Plex Mono" }} />
                <YAxis yAxisId="l" stroke="#71717A" tick={{ fontFamily: "IBM Plex Mono" }} />
                <YAxis yAxisId="r" orientation="right" stroke="#71717A" tick={{ fontFamily: "IBM Plex Mono" }} />
                <Tooltip contentStyle={{ background: "#141414", border: "1px solid #2A2A2A" }} />
                <Line yAxisId="l" type="monotone" dataKey="cost" stroke="#0055FF" dot={false} />
                <Line yAxisId="r" type="monotone" dataKey="latency" stroke="#FFCC00" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="k-card" data-testid="how-it-works">
        <div className="overline">Pipeline</div>
        <h2 className="text-2xl tracking-tight mt-1">How a Query Flows</h2>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-6 gap-2 font-mono text-xs">
          {[
            ["01", "Query analyzer", "intent + complexity"],
            ["02", "Privacy gate", "PII + policy check"],
            ["03", "Adaptive retrieval", "vector + OKF traversal"],
            ["04", "Evidence scoring", "relevance · authority"],
            ["05", "Router", "LOCAL · CLOUD · BOTH"],
            ["06", "Validation", "grounding · leakage"],
          ].map(([n, t, s]) => (
            <div key={n} className="border border-[#2A2A2A] p-3 hover:border-[#0055FF] transition-colors">
              <div className="text-[#71717A]">{n}</div>
              <div className="text-white mt-1">{t}</div>
              <div className="text-[#71717A] mt-1">{s}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
