"""
OKF Knowledge Engine: Structured knowledge repository, adaptive retrieval,
privacy classification, sanitization, and evidence scoring.
"""
from __future__ import annotations
import re
import math
import uuid
from datetime import datetime, timezone
from typing import Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


# ----- Privacy patterns (configurable policy engine) -----
PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Z|a-z]{2,}"),
    "phone": re.compile(r"\b(?:\+?\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "api_key": re.compile(r"(?i)\b(?:sk|api|key|token|secret)[-_][a-zA-Z0-9]{16,}\b"),
    "password": re.compile(r"(?i)password\s*[:=]\s*\S+"),
    "salary": re.compile(r"(?i)salary\s*(?:is|of|:)?\s*[₹$€£]?\s*[\d,]+"),
    "employee_id": re.compile(r"(?i)\bEMP[-_]?\d{3,}\b|\bemployee\s+id[:\s]+\S+"),
    "money_amount": re.compile(r"[₹$€£]\s*[\d,]+(?:\.\d+)?"),
}

SENSITIVE_KEYWORDS = {
    "confidential": ["confidential", "proprietary", "trade secret", "internal use only",
                     "restricted", "classified"],
    "financial": ["salary", "revenue", "profit", "loss", "acquisition", "merger",
                  "compensation", "bonus"],
    "personal": ["dob", "date of birth", "aadhaar", "passport", "license"],
}

SENSITIVITY_LEVELS = ["public", "internal", "confidential", "highly_sensitive"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify_sensitivity(text: str, declared: str | None = None) -> dict:
    """Return sensitivity classification with reasons and detected entities."""
    detected: dict[str, list[str]] = {}
    for name, pat in PII_PATTERNS.items():
        matches = pat.findall(text)
        if matches:
            detected[name] = list({m if isinstance(m, str) else str(m) for m in matches})[:5]

    reasons: list[str] = []
    score = 0
    if detected:
        reasons.append(f"PII detected: {', '.join(detected.keys())}")
        score += 2 * len(detected)

    text_l = text.lower()
    for cat, kws in SENSITIVE_KEYWORDS.items():
        hits = [k for k in kws if k in text_l]
        if hits:
            reasons.append(f"{cat} keywords: {', '.join(hits[:3])}")
            score += len(hits)

    if declared and declared in SENSITIVITY_LEVELS:
        level = declared
        reasons.append(f"user-declared: {declared}")
    elif score >= 4:
        level = "highly_sensitive"
    elif score >= 2:
        level = "confidential"
    elif score >= 1:
        level = "internal"
    else:
        level = "public"

    cloud_allowed = level in ("public", "internal")
    return {
        "level": level,
        "cloud_allowed": cloud_allowed,
        "score": score,
        "reasons": reasons or ["no sensitive markers found"],
        "detected_entities": detected,
    }


def sanitize_text(text: str, level: str = "confidential") -> dict:
    """Redact / abstract text before releasing to cloud. Returns sanitized text
    and a transformation log."""
    original = text
    transformations: list[dict] = []
    out = text

    # Always redact hard PII regardless
    replacements = {
        "email": "[EMAIL_REDACTED]",
        "phone": "[PHONE_REDACTED]",
        "ssn": "[SSN_REDACTED]",
        "credit_card": "[CARD_REDACTED]",
        "api_key": "[KEY_REDACTED]",
        "password": "password: [REDACTED]",
        "employee_id": "[EMP_ID_REDACTED]",
    }
    for name, pat in PII_PATTERNS.items():
        if name in replacements:
            matches = pat.findall(out)
            if matches:
                out = pat.sub(replacements[name], out)
                transformations.append({"type": "redact", "entity": name, "count": len(matches)})

    if level in ("confidential", "highly_sensitive"):
        # Abstract money values
        money_matches = PII_PATTERNS["money_amount"].findall(out)
        if money_matches:
            out = PII_PATTERNS["money_amount"].sub("[AMOUNT]", out)
            transformations.append({"type": "abstract", "entity": "money_amount",
                                    "count": len(money_matches)})
        salary_matches = PII_PATTERNS["salary"].findall(out)
        if salary_matches:
            out = PII_PATTERNS["salary"].sub("compensation info", out)
            transformations.append({"type": "abstract", "entity": "salary",
                                    "count": len(salary_matches)})
        # Replace proper names with placeholders (very simple heuristic)
        # Words of length>=3, capitalized, not at sentence start
        names = re.findall(r"(?<!^)(?<=[\.\s])([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})", out)
        for i, n in enumerate(names[:5]):
            out = out.replace(n, f"[PERSON_{chr(65+i)}]")
        if names:
            transformations.append({"type": "entity_replace", "entity": "person",
                                    "count": len(names)})

    return {
        "sanitized_text": out,
        "original_length": len(original),
        "sanitized_length": len(out),
        "transformations": transformations,
        "reduction_pct": round(100 * (1 - len(out) / max(len(original), 1)), 1),
    }


# ----- OKF knowledge node schema -----
def make_node(payload: dict) -> dict:
    """Normalize an OKF node with defaults."""
    text = payload.get("content", "")
    cls = classify_sensitivity(text, payload.get("sensitivity"))
    node = {
        "id": payload.get("id") or f"okf_{uuid.uuid4().hex[:10]}",
        "title": payload.get("title", "Untitled"),
        "type": payload.get("type", "document"),
        "source": payload.get("source", "manual"),
        "content": text,
        "version": payload.get("version", "1.0"),
        "authority": payload.get("authority", "internal"),
        "confidence": float(payload.get("confidence", 0.9)),
        "sensitivity": cls["level"],
        "processing": "local_only" if not cls["cloud_allowed"] else "local_or_cloud",
        "cloud_allowed": bool(payload.get("cloud_allowed_override", cls["cloud_allowed"])),
        "created_at": payload.get("created_at", now_iso()),
        "updated_at": now_iso(),
        "effective_date": payload.get("effective_date", now_iso()),
        "relationships": payload.get("relationships", []),
        "provenance": payload.get("provenance", {"origin": payload.get("source", "manual"),
                                                  "classifier": cls}),
        "tags": payload.get("tags", []),
    }
    return node


# ----- Adaptive Retrieval -----
class RetrievalEngine:
    """In-memory TF-IDF vector store combined with OKF graph traversal."""

    def __init__(self):
        self.nodes: dict[str, dict] = {}
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix = None
        self.node_ids: list[str] = []

    def rebuild(self, nodes: list[dict]):
        self.nodes = {n["id"]: n for n in nodes}
        self.node_ids = list(self.nodes.keys())
        corpus = [f"{n['title']}. {n['content']}" for n in nodes]
        if not corpus:
            self.vectorizer = None
            self.matrix = None
            return
        self.vectorizer = TfidfVectorizer(stop_words="english", max_features=4096,
                                          ngram_range=(1, 2))
        self.matrix = self.vectorizer.fit_transform(corpus)

    def vector_search(self, query: str, k: int = 5) -> list[dict]:
        if self.vectorizer is None or self.matrix is None or not self.node_ids:
            return []
        qv = self.vectorizer.transform([query])
        sims = cosine_similarity(qv, self.matrix)[0]
        idxs = np.argsort(-sims)[:k]
        return [{"node_id": self.node_ids[i], "score": float(sims[i]),
                 "method": "vector"} for i in idxs if sims[i] > 0.02]

    def okf_traverse(self, seed_ids: list[str], max_hops: int = 2) -> list[dict]:
        """BFS across relationships."""
        visited: set[str] = set()
        results: list[dict] = []
        frontier = [(sid, 0, "seed") for sid in seed_ids]
        while frontier:
            nid, hop, via = frontier.pop(0)
            if nid in visited or nid not in self.nodes:
                continue
            visited.add(nid)
            if hop > 0:
                results.append({"node_id": nid, "score": max(0.1, 1.0 - 0.3 * hop),
                                "method": "okf_traversal", "hops": hop, "via": via})
            if hop < max_hops:
                for rel in self.nodes[nid].get("relationships", []):
                    target = rel.get("target")
                    if target and target not in visited:
                        frontier.append((target, hop + 1, rel.get("type", "related_to")))
        return results

    def choose_strategy(self, query: str) -> str:
        q = query.lower()
        multihop_keywords = ["compare", "relationship", "depend", "impact", "cause",
                             "supersede", "contradict", "policy", "chain", "why",
                             "how does", "connected"]
        if any(k in q for k in multihop_keywords):
            return "hybrid"
        if "?" in q or len(q.split()) > 8:
            return "hybrid"
        return "vector"

    def adaptive_retrieve(self, query: str, k: int = 5) -> dict:
        strategy = self.choose_strategy(query)
        vec_hits = self.vector_search(query, k=k)
        okf_hits: list[dict] = []
        if strategy in ("hybrid", "okf") and vec_hits:
            seed_ids = [h["node_id"] for h in vec_hits[:3]]
            okf_hits = self.okf_traverse(seed_ids, max_hops=2)
        combined: dict[str, dict] = {}
        for h in vec_hits + okf_hits:
            nid = h["node_id"]
            if nid not in combined or h["score"] > combined[nid]["score"]:
                combined[nid] = h
        return {
            "strategy": strategy,
            "vector_hits": vec_hits,
            "okf_hits": okf_hits,
            "combined": sorted(combined.values(), key=lambda x: -x["score"]),
        }


# ----- Evidence scoring -----
def score_evidence(evidence: list[dict], nodes_by_id: dict[str, dict]) -> dict:
    if not evidence:
        return {"score": 0.0, "relevance": 0, "completeness": 0, "authority": 0,
                "diversity": 0, "count": 0, "verdict": "insufficient"}
    scores = [e["score"] for e in evidence]
    relevance = float(np.mean(scores))
    completeness = min(1.0, len(evidence) / 5)
    authorities = [nodes_by_id.get(e["node_id"], {}).get("confidence", 0.5) for e in evidence]
    authority = float(np.mean(authorities))
    types = {nodes_by_id.get(e["node_id"], {}).get("type", "doc") for e in evidence}
    diversity = min(1.0, len(types) / 3)
    overall = 0.4 * relevance + 0.25 * completeness + 0.25 * authority + 0.1 * diversity
    verdict = "high" if overall > 0.6 else "medium" if overall > 0.35 else "low"
    return {
        "score": round(overall, 3),
        "relevance": round(relevance, 3),
        "completeness": round(completeness, 3),
        "authority": round(authority, 3),
        "diversity": round(diversity, 3),
        "count": len(evidence),
        "verdict": verdict,
    }


# ----- Model router -----
LOCAL_MODEL = {"provider": "openai", "model": "gpt-5.4-mini",
               "cost_per_1k_input": 0.0001, "cost_per_1k_output": 0.0004}
CLOUD_MODEL = {"provider": "openai", "model": "gpt-5.4",
               "cost_per_1k_input": 0.0025, "cost_per_1k_output": 0.01}


def route_execution(evidence: list[dict], nodes_by_id: dict[str, dict],
                    query_complexity: str, user_pref: str = "auto",
                    remaining_budget: float = 100.0) -> dict:
    """Decide LOCAL / CLOUD / BOTH based on privacy hard constraints and utility."""
    if user_pref in ("local", "cloud", "both"):
        chosen = user_pref
        override = True
    else:
        override = False
        chosen = None

    # Analyze evidence sensitivity
    ev_nodes = [nodes_by_id.get(e["node_id"]) for e in evidence]
    ev_nodes = [n for n in ev_nodes if n]
    has_private = any(not n.get("cloud_allowed", True) for n in ev_nodes)
    has_public = any(n.get("cloud_allowed", True) for n in ev_nodes)
    all_private = has_private and not has_public
    reasons: list[str] = []

    if not chosen:
        if all_private:
            chosen = "local"
            reasons.append("all retrieved evidence is local-only (privacy hard constraint)")
        elif has_private and has_public and query_complexity in ("high", "medium"):
            chosen = "both"
            reasons.append("mixed sensitivity + complex query → collaborative local+cloud")
        elif query_complexity == "high" and remaining_budget > 0.5:
            chosen = "cloud"
            reasons.append("complex query, no private constraints, cloud budget available")
        elif query_complexity == "low":
            chosen = "local"
            reasons.append("simple query answerable locally")
        else:
            chosen = "local"
            reasons.append("default safe: local execution")
    else:
        # If user forced cloud but private evidence present, downgrade for safety
        if chosen == "cloud" and has_private:
            chosen = "both"
            reasons.append("user requested cloud but private evidence present → forced BOTH mode")
        else:
            reasons.append(f"user override: {user_pref}")

    # Privacy exposure estimate
    exposure = 0.0
    if chosen == "cloud":
        exposure = 0.7 if has_private else 0.1
    elif chosen == "both":
        exposure = 0.3
    else:
        exposure = 0.0

    return {
        "mode": chosen,
        "reasons": reasons,
        "override": override,
        "has_private_evidence": has_private,
        "has_public_evidence": has_public,
        "estimated_privacy_exposure": exposure,
        "local_model": LOCAL_MODEL,
        "cloud_model": CLOUD_MODEL,
    }


def estimate_cost(prompt_tokens: int, output_tokens: int, model: dict) -> float:
    return round(prompt_tokens / 1000 * model["cost_per_1k_input"] +
                 output_tokens / 1000 * model["cost_per_1k_output"], 6)


def query_complexity(query: str) -> str:
    words = len(query.split())
    if words > 25 or "compare" in query.lower() or "analyze" in query.lower():
        return "high"
    if words > 10:
        return "medium"
    return "low"


# ----- Response validation -----
def validate_response(answer: str, evidence_texts: list[str],
                      private_content: list[str]) -> dict:
    checks: list[dict] = []
    # 1. Evidence support: overlap with evidence corpus
    ans_words = set(re.findall(r"\b\w{4,}\b", answer.lower()))
    ev_words = set()
    for t in evidence_texts:
        ev_words |= set(re.findall(r"\b\w{4,}\b", t.lower()))
    overlap = len(ans_words & ev_words) / max(len(ans_words), 1)
    checks.append({"name": "evidence_support", "score": round(overlap, 3),
                   "passed": overlap > 0.15})

    # 2. Privacy leakage: private content should not leak
    leaked_terms: list[str] = []
    for priv in private_content:
        priv_terms = re.findall(r"\b[A-Z][a-zA-Z]{3,}\b|[\d,]{5,}", priv)
        for term in priv_terms:
            if term in answer and term not in " ".join(evidence_texts):
                leaked_terms.append(term)
    checks.append({"name": "privacy_leakage",
                   "score": 1.0 if not leaked_terms else 0.0,
                   "passed": not leaked_terms,
                   "details": leaked_terms[:5]})

    # 3. PII in output
    pii_in_output: list[str] = []
    for name, pat in PII_PATTERNS.items():
        if name in ("money_amount",):
            continue
        if pat.search(answer):
            pii_in_output.append(name)
    checks.append({"name": "no_pii_in_output",
                   "score": 1.0 if not pii_in_output else 0.0,
                   "passed": not pii_in_output,
                   "details": pii_in_output})

    # 4. Citation presence
    has_citation = bool(re.search(r"\[[^\]]+\]|source:|according to", answer.lower()))
    checks.append({"name": "citation_present",
                   "score": 1.0 if has_citation else 0.5,
                   "passed": True})

    all_passed = all(c["passed"] for c in checks)
    overall = float(np.mean([c["score"] for c in checks]))
    return {
        "passed": all_passed,
        "overall_score": round(overall, 3),
        "checks": checks,
    }
