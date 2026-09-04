"""
Hybrid RAG + OKF Backend
FastAPI server with adaptive retrieval, privacy-aware routing, and LLM execution.
"""
from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import time
import uuid
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime, timezone

from emergentintegrations.llm.chat import LlmChat, UserMessage

from okf_engine import (
    RetrievalEngine, make_node, classify_sensitivity, sanitize_text,
    score_evidence, route_execution, estimate_cost, query_complexity,
    validate_response, now_iso, LOCAL_MODEL, CLOUD_MODEL,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

app = FastAPI(title="OKF Hybrid RAG")
api_router = APIRouter(prefix="/api")
logger = logging.getLogger("okf")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s - %(message)s")

retrieval = RetrievalEngine()


# ---------- Bootstrap: seed sample data if empty ----------
SEED_NODES = [
    {
        "title": "Internal Financial Policy 2025",
        "type": "policy",
        "source": "internal_financial_policy.pdf",
        "authority": "official",
        "confidence": 0.97,
        "sensitivity": "confidential",
        "content": (
            "Confidential internal financial policy. Employee salary bands are set "
            "quarterly. Bonuses tied to KPIs. Employee EMP-4521 receives compensation "
            "of ₹18,00,000 annually. All revenue projections are proprietary."
        ),
        "tags": ["policy", "finance", "internal"],
    },
    {
        "title": "Employee Handbook Section 4 - Compensation",
        "type": "policy",
        "source": "handbook.pdf",
        "authority": "official",
        "confidence": 0.95,
        "sensitivity": "confidential",
        "content": (
            "Compensation review occurs every 6 months. Managers assess performance "
            "against agreed KPIs. See internal financial policy for salary bands. "
            "Contact hr@company.com for questions."
        ),
        "tags": ["hr", "internal"],
    },
    {
        "title": "Global Industry Trends Report 2025",
        "type": "industry_report",
        "source": "public_report.pdf",
        "authority": "external",
        "confidence": 0.91,
        "sensitivity": "public",
        "content": (
            "The global tech industry grew 8.3% in 2024. AI and cloud services led the "
            "expansion. Average compensation in the AI sector rose 12% year-over-year. "
            "Companies invested heavily in retrieval-augmented systems."
        ),
        "tags": ["industry", "public", "trends"],
    },
    {
        "title": "OKF Specification Overview",
        "type": "specification",
        "source": "okf_spec.md",
        "authority": "external",
        "confidence": 0.99,
        "sensitivity": "public",
        "content": (
            "The Open Knowledge Format (OKF) defines structured knowledge nodes with "
            "explicit metadata: sensitivity, provenance, relationships (related_to, "
            "derived_from, contradicts, supersedes). It enables multi-hop retrieval "
            "and provenance-aware AI systems."
        ),
        "tags": ["okf", "spec"],
    },
    {
        "title": "RAG Best Practices Whitepaper",
        "type": "whitepaper",
        "source": "rag_whitepaper.pdf",
        "authority": "external",
        "confidence": 0.88,
        "sensitivity": "public",
        "content": (
            "Retrieval-augmented generation combines vector search with LLMs. Hybrid "
            "systems that mix vector similarity with structured graph traversal reduce "
            "hallucinations and improve multi-hop answering accuracy."
        ),
        "tags": ["rag", "public"],
    },
]


async def bootstrap_seed():
    count = await db.okf_nodes.count_documents({})
    if count == 0:
        nodes = []
        for s in SEED_NODES:
            n = make_node(s)
            nodes.append(n)
        # Add sample relationships
        nodes[1]["relationships"] = [
            {"target": nodes[0]["id"], "type": "references"},
        ]
        nodes[0]["relationships"] = [
            {"target": nodes[1]["id"], "type": "related_to"},
        ]
        nodes[2]["relationships"] = [
            {"target": nodes[4]["id"], "type": "related_to"},
        ]
        nodes[4]["relationships"] = [
            {"target": nodes[3]["id"], "type": "derived_from"},
        ]
        await db.okf_nodes.insert_many([{**n, "_id": n["id"]} for n in nodes])
        logger.info(f"seeded {len(nodes)} OKF nodes")
    await refresh_retrieval_index()


async def refresh_retrieval_index():
    docs = await db.okf_nodes.find({}, {"_id": 0}).to_list(1000)
    retrieval.rebuild(docs)
    logger.info(f"retrieval index rebuilt: {len(docs)} nodes")


# ---------- Models ----------
class NodeIn(BaseModel):
    title: str
    content: str
    type: str = "document"
    source: str = "manual"
    authority: str = "internal"
    confidence: float = 0.9
    sensitivity: Optional[str] = None
    cloud_allowed_override: Optional[bool] = None
    tags: list[str] = []
    relationships: list[dict] = []


class QueryIn(BaseModel):
    query: str
    mode: str = "auto"  # auto | local | cloud | both
    top_k: int = 5


# ---------- Basic endpoints ----------
@api_router.get("/")
async def root():
    return {"service": "OKF Hybrid RAG", "status": "ok", "time": now_iso()}


@api_router.get("/health")
async def health():
    node_count = await db.okf_nodes.count_documents({})
    trace_count = await db.traces.count_documents({})
    return {"ok": True, "nodes": node_count, "traces": trace_count,
            "llm_key_configured": bool(EMERGENT_LLM_KEY)}


# ---------- Knowledge base ----------
@api_router.get("/knowledge")
async def list_nodes():
    docs = await db.okf_nodes.find({}, {"_id": 0}).sort("updated_at", -1).to_list(500)
    return docs


@api_router.get("/knowledge/{node_id}")
async def get_node(node_id: str):
    doc = await db.okf_nodes.find_one({"id": node_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "node not found")
    return doc


@api_router.post("/knowledge")
async def add_node(payload: NodeIn):
    node = make_node(payload.model_dump())
    await db.okf_nodes.insert_one({**node, "_id": node["id"]})
    await refresh_retrieval_index()
    return node


@api_router.delete("/knowledge/{node_id}")
async def delete_node(node_id: str):
    await db.okf_nodes.delete_one({"id": node_id})
    await refresh_retrieval_index()
    return {"deleted": node_id}


@api_router.post("/knowledge/{node_id}/classify")
async def reclassify(node_id: str):
    doc = await db.okf_nodes.find_one({"id": node_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "node not found")
    cls = classify_sensitivity(doc["content"])
    return {"node_id": node_id, "classification": cls}


# ---------- Retrieve only (debug) ----------
@api_router.post("/retrieve")
async def do_retrieve(payload: QueryIn):
    result = retrieval.adaptive_retrieve(payload.query, k=payload.top_k)
    nodes_by_id = {nid: retrieval.nodes[nid] for nid in retrieval.nodes}
    result["evidence_quality"] = score_evidence(result["combined"], nodes_by_id)
    return result


# ---------- Sanitize preview ----------
@api_router.post("/sanitize")
async def do_sanitize(payload: dict):
    return sanitize_text(payload.get("text", ""), payload.get("level", "confidential"))


# ---------- LLM execution helpers ----------
async def call_llm(system: str, user_text: str, model_spec: dict,
                   session_id: str) -> dict:
    if not EMERGENT_LLM_KEY:
        return {"text": "[LLM_KEY_MISSING] Configure EMERGENT_LLM_KEY.",
                "tokens_in": 0, "tokens_out": 0, "error": "no_key"}
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=session_id,
                   system_message=system).with_model(model_spec["provider"],
                                                     model_spec["model"])
    try:
        response = await asyncio.wait_for(
            chat.send_message(UserMessage(text=user_text)), timeout=45.0
        )
        text = response if isinstance(response, str) else str(response)
        tokens_in = max(1, len(user_text) // 4)
        tokens_out = max(1, len(text) // 4)
        return {"text": text, "tokens_in": tokens_in, "tokens_out": tokens_out,
                "model": model_spec["model"]}
    except Exception as e:
        logger.exception("llm call failed")
        return {"text": f"[LLM_ERROR: {type(e).__name__}] {str(e)[:200]}",
                "tokens_in": 0, "tokens_out": 0, "error": str(e)[:200]}


def build_evidence_block(evidence: list[dict], nodes_by_id: dict,
                         sanitize_private: bool = False) -> tuple[str, list[dict]]:
    """Return prompt block + list of used sources with what was sanitized."""
    lines = []
    used = []
    for i, e in enumerate(evidence, 1):
        n = nodes_by_id.get(e["node_id"])
        if not n:
            continue
        content = n["content"]
        transformations: list[dict] = []
        if sanitize_private and not n.get("cloud_allowed", True):
            san = sanitize_text(content, n.get("sensitivity", "confidential"))
            content = san["sanitized_text"]
            transformations = san["transformations"]
        lines.append(f"[SOURCE {i}] {n['title']} (id={n['id']}, "
                     f"sensitivity={n['sensitivity']}, authority={n['authority']})\n{content}")
        used.append({
            "source_index": i,
            "node_id": n["id"],
            "title": n["title"],
            "sensitivity": n["sensitivity"],
            "cloud_allowed": n.get("cloud_allowed", True),
            "sanitized": bool(transformations),
            "transformations": transformations,
            "score": e.get("score"),
            "method": e.get("method"),
        })
    return "\n\n".join(lines), used


SYSTEM_LOCAL = (
    "You are a LOCAL research assistant running on-device. You have access to full "
    "private documents. Answer strictly using the provided SOURCES. Cite sources as "
    "[SOURCE N]. If evidence is insufficient say so. Do not fabricate."
)
SYSTEM_CLOUD = (
    "You are a CLOUD research assistant. Answer using only the provided SOURCES. "
    "Sanitized/redacted markers may appear ([EMAIL_REDACTED], [PERSON_A], [AMOUNT]) — "
    "respect them and do not attempt to reconstruct redacted values. Cite [SOURCE N]."
)
SYSTEM_FUSION = (
    "You are the FINAL VALIDATOR combining a LOCAL analysis (based on private data) and "
    "a CLOUD analysis (based on public data). Merge them into a single coherent answer, "
    "prefer local facts for private aspects and cloud facts for public aspects. Cite "
    "[LOCAL] and [CLOUD] appropriately. Never leak specific private identifiers."
)


# ---------- Main query endpoint ----------
@api_router.post("/query")
async def do_query(payload: QueryIn):
    q_id = f"q_{uuid.uuid4().hex[:10]}"
    started = time.time()
    trace: dict[str, Any] = {"query_id": q_id, "query": payload.query,
                              "mode_requested": payload.mode, "started_at": now_iso()}

    # Step 1: query privacy classification
    q_cls = classify_sensitivity(payload.query)
    trace["query_classification"] = q_cls
    complexity = query_complexity(payload.query)
    trace["complexity"] = complexity

    # Step 2: adaptive retrieval
    ret = retrieval.adaptive_retrieve(payload.query, k=payload.top_k)
    trace["retrieval_strategy"] = ret["strategy"]
    trace["vector_hits"] = ret["vector_hits"]
    trace["okf_hits"] = ret["okf_hits"]
    trace["combined_evidence"] = ret["combined"]

    nodes_by_id = {nid: retrieval.nodes[nid] for nid in retrieval.nodes}
    evidence_quality = score_evidence(ret["combined"], nodes_by_id)
    trace["evidence_quality"] = evidence_quality

    if not ret["combined"]:
        trace["final_answer"] = ("No relevant knowledge found in the OKF repository. "
                                  "Please add documents or refine the query.")
        trace["validation"] = {"passed": True, "overall_score": 1.0, "checks": []}
        trace["execution_mode"] = "none"
        trace["cost"] = 0.0
        trace["latency_ms"] = int((time.time() - started) * 1000)
        trace["finished_at"] = now_iso()
        await db.traces.insert_one({**trace, "_id": q_id})
        return trace

    # Step 3: routing decision
    routing = route_execution(ret["combined"], nodes_by_id, complexity, payload.mode)
    trace["routing"] = routing
    mode = routing["mode"]
    trace["execution_mode"] = mode

    # Step 4: execute according to mode
    private_texts = [nodes_by_id[e["node_id"]]["content"]
                     for e in ret["combined"]
                     if not nodes_by_id[e["node_id"]].get("cloud_allowed", True)]

    local_answer, cloud_answer, final_answer = "", "", ""
    cost_total = 0.0
    tokens_total = {"in": 0, "out": 0}
    sources_used: list[dict] = []
    cloud_release_log: list[dict] = []

    if mode in ("local", "both"):
        # Local uses full evidence (no sanitization)
        block, used = build_evidence_block(ret["combined"], nodes_by_id,
                                            sanitize_private=False)
        sources_used.extend(used)
        prompt = f"QUESTION:\n{payload.query}\n\nSOURCES:\n{block}\n\nANSWER:"
        res = await call_llm(SYSTEM_LOCAL, prompt, LOCAL_MODEL, q_id + "_local")
        local_answer = res["text"]
        cost_total += estimate_cost(res["tokens_in"], res["tokens_out"], LOCAL_MODEL)
        tokens_total["in"] += res["tokens_in"]
        tokens_total["out"] += res["tokens_out"]
        trace["local_execution"] = {"model": LOCAL_MODEL["model"],
                                     "tokens_in": res["tokens_in"],
                                     "tokens_out": res["tokens_out"],
                                     "answer_preview": local_answer[:200]}

    if mode in ("cloud", "both"):
        # Cloud gets only cloud_allowed evidence OR sanitized private evidence
        if mode == "cloud":
            allowed = [e for e in ret["combined"]
                       if nodes_by_id[e["node_id"]].get("cloud_allowed", True)]
        else:
            allowed = ret["combined"]  # sanitize private in build
        block, used = build_evidence_block(allowed, nodes_by_id, sanitize_private=True)
        cloud_release_log = [u for u in used if u.get("sanitized")] + \
                            [u for u in used if not u.get("sanitized")]
        sources_used.extend(used)
        if not block:
            cloud_answer = "[NO_CLOUD_ELIGIBLE_EVIDENCE]"
        else:
            prompt = f"QUESTION:\n{payload.query}\n\nSOURCES:\n{block}\n\nANSWER:"
            res = await call_llm(SYSTEM_CLOUD, prompt, CLOUD_MODEL, q_id + "_cloud")
            cloud_answer = res["text"]
            cost_total += estimate_cost(res["tokens_in"], res["tokens_out"], CLOUD_MODEL)
            tokens_total["in"] += res["tokens_in"]
            tokens_total["out"] += res["tokens_out"]
            trace["cloud_execution"] = {"model": CLOUD_MODEL["model"],
                                         "tokens_in": res["tokens_in"],
                                         "tokens_out": res["tokens_out"],
                                         "answer_preview": cloud_answer[:200],
                                         "released_sources": cloud_release_log}

    if mode == "both":
        fusion_prompt = (f"QUESTION: {payload.query}\n\n"
                          f"[LOCAL ANALYSIS]\n{local_answer}\n\n"
                          f"[CLOUD ANALYSIS]\n{cloud_answer}\n\n"
                          "Produce the final answer:")
        res = await call_llm(SYSTEM_FUSION, fusion_prompt, LOCAL_MODEL,
                              q_id + "_fusion")
        final_answer = res["text"]
        cost_total += estimate_cost(res["tokens_in"], res["tokens_out"], LOCAL_MODEL)
        tokens_total["in"] += res["tokens_in"]
        tokens_total["out"] += res["tokens_out"]
        trace["fusion"] = {"tokens_in": res["tokens_in"],
                           "tokens_out": res["tokens_out"]}
    elif mode == "local":
        final_answer = local_answer
    else:
        final_answer = cloud_answer

    trace["final_answer"] = final_answer
    trace["sources_used"] = sources_used
    trace["cloud_release_log"] = cloud_release_log

    # Step 5: validation
    ev_texts = [nodes_by_id[e["node_id"]]["content"] for e in ret["combined"]]
    validation = validate_response(final_answer, ev_texts, private_texts)
    trace["validation"] = validation

    trace["cost"] = round(cost_total, 6)
    trace["tokens"] = tokens_total
    trace["latency_ms"] = int((time.time() - started) * 1000)
    trace["finished_at"] = now_iso()
    trace["final_confidence"] = round(0.5 * evidence_quality["score"]
                                       + 0.5 * validation["overall_score"], 3)

    await db.traces.insert_one({**trace, "_id": q_id})
    return trace


# ---------- Traces & observability ----------
@api_router.get("/traces")
async def list_traces(limit: int = 50):
    docs = await db.traces.find({}, {"_id": 0, "vector_hits": 0, "okf_hits": 0,
                                       "combined_evidence": 0, "sources_used": 0,
                                       "cloud_release_log": 0}
                                 ).sort("started_at", -1).to_list(limit)
    return docs


@api_router.get("/traces/{query_id}")
async def get_trace(query_id: str):
    doc = await db.traces.find_one({"query_id": query_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "trace not found")
    return doc


@api_router.get("/stats")
async def stats():
    traces = await db.traces.find({}, {"_id": 0}).to_list(1000)
    total = len(traces)
    if total == 0:
        return {"total_queries": 0, "total_cost": 0.0, "avg_latency_ms": 0,
                "by_mode": {}, "avg_confidence": 0.0,
                "avg_evidence": 0.0, "avg_validation": 0.0,
                "recent_costs": []}
    modes = {}
    for t in traces:
        m = t.get("execution_mode", "unknown")
        modes[m] = modes.get(m, 0) + 1
    total_cost = sum(t.get("cost", 0) for t in traces)
    avg_lat = sum(t.get("latency_ms", 0) for t in traces) / total
    avg_conf = sum(t.get("final_confidence", 0) for t in traces) / total
    avg_ev = sum((t.get("evidence_quality") or {}).get("score", 0) for t in traces) / total
    avg_val = sum((t.get("validation") or {}).get("overall_score", 0) for t in traces) / total
    return {
        "total_queries": total,
        "total_cost": round(total_cost, 4),
        "avg_latency_ms": int(avg_lat),
        "by_mode": modes,
        "avg_confidence": round(avg_conf, 3),
        "avg_evidence": round(avg_ev, 3),
        "avg_validation": round(avg_val, 3),
        "recent_costs": [{"query_id": t["query_id"], "cost": t.get("cost", 0),
                           "mode": t.get("execution_mode"),
                           "latency": t.get("latency_ms")}
                          for t in traces[-20:]],
    }


@api_router.get("/privacy/audit")
async def privacy_audit():
    traces = await db.traces.find({}, {"_id": 0}).sort("started_at", -1).to_list(200)
    events = []
    for t in traces:
        for src in t.get("cloud_release_log") or []:
            events.append({
                "query_id": t["query_id"],
                "started_at": t.get("started_at"),
                "mode": t.get("execution_mode"),
                "node_id": src.get("node_id"),
                "title": src.get("title"),
                "sensitivity": src.get("sensitivity"),
                "sanitized": src.get("sanitized"),
                "transformations": src.get("transformations", []),
            })
    return {"events": events[:200], "total_events": len(events)}


# ---------- Benchmark ----------
BENCHMARK_QUERIES = [
    "What is the Open Knowledge Format?",
    "Compare our company compensation with industry trends.",
    "How does RAG reduce hallucination?",
    "What is our employee compensation policy?",
    "What are current AI industry growth rates?",
]


@api_router.post("/benchmark")
async def run_benchmark():
    configs = [
        {"name": "Vector-only + Cloud", "mode": "cloud", "disable_okf": True},
        {"name": "Vector-only + Local", "mode": "local", "disable_okf": True},
        {"name": "OKF Hybrid + Local", "mode": "local"},
        {"name": "OKF Hybrid + Cloud", "mode": "cloud"},
        {"name": "OKF Hybrid + BOTH (Proposed)", "mode": "both"},
        {"name": "OKF Hybrid + Auto Routing (Proposed)", "mode": "auto"},
    ]
    results = []
    for cfg in configs:
        acc_ev, acc_val, acc_cost, acc_lat, priv_leaks = [], [], [], [], 0
        for q in BENCHMARK_QUERIES:
            r = await do_query(QueryIn(query=q, mode=cfg["mode"]))
            acc_ev.append((r.get("evidence_quality") or {}).get("score", 0))
            acc_val.append((r.get("validation") or {}).get("overall_score", 0))
            acc_cost.append(r.get("cost", 0))
            acc_lat.append(r.get("latency_ms", 0))
            if not (r.get("validation") or {}).get("passed", True):
                priv_leaks += 1
        results.append({
            "config": cfg["name"],
            "mode": cfg["mode"],
            "queries": len(BENCHMARK_QUERIES),
            "avg_evidence": round(sum(acc_ev) / len(acc_ev), 3),
            "avg_validation": round(sum(acc_val) / len(acc_val), 3),
            "avg_cost": round(sum(acc_cost) / len(acc_cost), 6),
            "avg_latency_ms": int(sum(acc_lat) / len(acc_lat)),
            "validation_failures": priv_leaks,
        })
    doc = {"id": f"bench_{uuid.uuid4().hex[:8]}", "at": now_iso(), "results": results}
    await db.benchmarks.insert_one({**doc, "_id": doc["id"]})
    return doc


@api_router.get("/benchmark")
async def get_benchmarks():
    docs = await db.benchmarks.find({}, {"_id": 0}).sort("at", -1).to_list(20)
    return docs


# ---------- App setup ----------
app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup():
    await bootstrap_seed()


@app.on_event("shutdown")
async def _shutdown():
    client.close()
