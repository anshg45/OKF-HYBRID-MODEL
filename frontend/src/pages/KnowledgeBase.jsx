import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { SensitivityPill } from "../components/PillBadge";
import { Plus, Trash2, X } from "lucide-react";
import { toast } from "sonner";

export default function KnowledgeBase() {
  const [nodes, setNodes] = useState([]);
  const [selected, setSelected] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({
    title: "", content: "", type: "document", source: "manual",
    authority: "internal", sensitivity: "",
  });

  const load = () => api.get("/knowledge").then((r) => setNodes(r.data));
  useEffect(() => { load(); }, []);

  const add = async () => {
    if (!form.title || !form.content) {
      toast.error("Title and content are required");
      return;
    }
    const payload = { ...form };
    if (!payload.sensitivity) delete payload.sensitivity;
    const r = await api.post("/knowledge", payload);
    toast.success(`Node added — classified as ${r.data.sensitivity}`);
    setShowAdd(false);
    setForm({ title: "", content: "", type: "document", source: "manual",
              authority: "internal", sensitivity: "" });
    load();
  };

  const remove = async (id) => {
    await api.delete(`/knowledge/${id}`);
    toast.success("Node removed");
    if (selected?.id === id) setSelected(null);
    load();
  };

  return (
    <div className="flex-1 flex overflow-hidden" data-testid="kb-root">
      <div className="flex-1 p-8 overflow-y-auto">
        <div className="flex items-start justify-between">
          <div>
            <div className="overline">Repository</div>
            <h1 className="text-4xl sm:text-5xl tracking-tight mt-1">Knowledge Base</h1>
            <p className="text-sm text-[#A1A1AA] mt-2 max-w-xl">
              OKF nodes with sensitivity, authority, and relationship metadata.
              Every node is auto-classified for privacy before it enters the retrieval index.
            </p>
          </div>
          <button
            data-testid="add-node-btn"
            className="k-btn k-btn-primary flex items-center gap-2"
            onClick={() => setShowAdd(true)}
          >
            <Plus size={14} strokeWidth={2} /> Add Node
          </button>
        </div>

        <div className="mt-6 border border-[#2A2A2A]" data-testid="kb-table">
          <table className="w-full text-sm mono">
            <thead>
              <tr className="border-b border-[#2A2A2A] text-[#71717A] text-xs uppercase tracking-wider">
                <th className="text-left px-4 py-3">ID</th>
                <th className="text-left px-4 py-3">Title</th>
                <th className="text-left px-4 py-3">Type</th>
                <th className="text-left px-4 py-3">Authority</th>
                <th className="text-left px-4 py-3">Sensitivity</th>
                <th className="text-left px-4 py-3">Cloud</th>
                <th className="text-left px-4 py-3">Confidence</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {nodes.length === 0 && (
                <tr><td colSpan={8} className="p-8 text-center text-[#71717A]">No nodes yet.</td></tr>
              )}
              {nodes.map((n) => (
                <tr
                  key={n.id}
                  className="row-hover border-b border-[#1A1A1A] cursor-pointer"
                  onClick={() => setSelected(n)}
                  data-testid={`kb-row-${n.id}`}
                >
                  <td className="px-4 py-3 text-[#71717A]">{n.id.slice(0, 12)}…</td>
                  <td className="px-4 py-3 text-white">{n.title}</td>
                  <td className="px-4 py-3 text-[#A1A1AA]">{n.type}</td>
                  <td className="px-4 py-3 text-[#A1A1AA]">{n.authority}</td>
                  <td className="px-4 py-3"><SensitivityPill level={n.sensitivity} /></td>
                  <td className="px-4 py-3">
                    <span className={`pill ${n.cloud_allowed ? "pill-green" : "pill-red"}`}>
                      {n.cloud_allowed ? "allowed" : "blocked"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-[#A1A1AA]">{n.confidence?.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={(e) => { e.stopPropagation(); remove(n.id); }}
                      className="text-[#71717A] hover:text-[#FF3B30]"
                      data-testid={`delete-${n.id}`}
                    >
                      <Trash2 size={14} strokeWidth={1.5} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {selected && (
        <div className="w-[420px] border-l border-[#2A2A2A] bg-[#141414] overflow-y-auto" data-testid="node-detail">
          <div className="p-6 border-b border-[#2A2A2A] flex items-start justify-between">
            <div>
              <div className="overline">Node</div>
              <div className="text-lg mt-1 tracking-tight">{selected.title}</div>
              <div className="text-[11px] text-[#71717A] mono mt-1">{selected.id}</div>
            </div>
            <button onClick={() => setSelected(null)} className="text-[#71717A] hover:text-white">
              <X size={16} />
            </button>
          </div>
          <div className="p-6 space-y-4 text-sm">
            <div className="flex flex-wrap gap-2">
              <SensitivityPill level={selected.sensitivity} />
              <span className="pill">{selected.type}</span>
              <span className="pill">{selected.authority}</span>
              <span className={`pill ${selected.cloud_allowed ? "pill-green" : "pill-red"}`}>
                {selected.cloud_allowed ? "cloud ok" : "local only"}
              </span>
            </div>
            <div>
              <div className="overline mb-2">Content</div>
              <pre className="mono text-xs whitespace-pre-wrap text-[#A1A1AA] bg-[#0F0F0F] border border-[#2A2A2A] p-3 max-h-64 overflow-y-auto">
                {selected.content}
              </pre>
            </div>
            <div>
              <div className="overline mb-2">Provenance</div>
              <div className="mono text-xs text-[#A1A1AA]">
                <div>source: <span className="text-white">{selected.source}</span></div>
                <div>version: {selected.version}</div>
                <div>confidence: {selected.confidence}</div>
                <div>updated: {selected.updated_at?.slice(0, 19)}</div>
              </div>
            </div>
            <div>
              <div className="overline mb-2">Detected Entities</div>
              <div className="mono text-xs text-[#A1A1AA]">
                {Object.entries(selected.provenance?.classifier?.detected_entities || {}).length === 0
                  ? <span className="text-[#71717A]">none</span>
                  : Object.entries(selected.provenance.classifier.detected_entities).map(([k, v]) => (
                      <div key={k}>{k}: <span className="text-[#FFCC00]">{v.length}</span></div>
                    ))}
              </div>
            </div>
            <div>
              <div className="overline mb-2">Relationships</div>
              {(selected.relationships || []).length === 0 && (
                <div className="text-xs text-[#71717A] mono">none</div>
              )}
              {(selected.relationships || []).map((r, i) => (
                <div key={i} className="mono text-xs text-[#A1A1AA] py-1">
                  <span className="text-[#0055FF]">{r.type}</span> → {r.target}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {showAdd && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50" data-testid="add-modal">
          <div className="k-card w-full max-w-2xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl tracking-tight">Add OKF Node</h2>
              <button onClick={() => setShowAdd(false)} className="text-[#71717A] hover:text-white">
                <X size={18} />
              </button>
            </div>
            <div className="space-y-3">
              <input className="k-input" placeholder="Title"
                data-testid="node-title-input"
                value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
              <textarea className="k-textarea" rows={8}
                data-testid="node-content-input"
                placeholder="Content (raw text — will be classified for sensitivity automatically)"
                value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} />
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                <select className="k-select" value={form.type}
                  onChange={(e) => setForm({ ...form, type: e.target.value })}>
                  <option value="document">document</option>
                  <option value="policy">policy</option>
                  <option value="industry_report">industry_report</option>
                  <option value="whitepaper">whitepaper</option>
                  <option value="specification">specification</option>
                </select>
                <select className="k-select" value={form.authority}
                  onChange={(e) => setForm({ ...form, authority: e.target.value })}>
                  <option value="internal">internal</option>
                  <option value="official">official</option>
                  <option value="external">external</option>
                  <option value="community">community</option>
                </select>
                <select className="k-select" value={form.sensitivity}
                  onChange={(e) => setForm({ ...form, sensitivity: e.target.value })}>
                  <option value="">auto-classify</option>
                  <option value="public">public</option>
                  <option value="internal">internal</option>
                  <option value="confidential">confidential</option>
                  <option value="highly_sensitive">highly_sensitive</option>
                </select>
                <input className="k-input" placeholder="source"
                  value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button className="k-btn" onClick={() => setShowAdd(false)}>Cancel</button>
                <button className="k-btn k-btn-primary" onClick={add} data-testid="submit-node-btn">
                  Classify &amp; Add
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
