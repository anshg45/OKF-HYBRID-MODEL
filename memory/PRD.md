# OKF Hybrid RAG - Research Prototype PRD

## Original Problem Statement
Full-stack research-grade prototype for a Hybrid RAG + LLM system using Google
Open Knowledge Format (OKF) as structured knowledge backbone. Supports LOCAL,
CLOUD, and BOTH (collaborative) execution modes. Central objective: maximise
answer quality while minimising cloud cost, latency, and privacy exposure —
with privacy as a HARD constraint.

## Architecture
- Backend: FastAPI (`/app/backend/server.py`) + OKF engine (`okf_engine.py`)
- Storage: MongoDB (`okf_nodes`, `traces`, `benchmarks`)
- LLM: emergentintegrations LlmChat with EMERGENT_LLM_KEY
  - "Cloud" model: openai/gpt-5.4
  - "Local" model (simulated): openai/gpt-5.4-mini
- Retrieval: In-memory TF-IDF vector search (sklearn) + OKF relationship traversal
- Frontend: React + Tailwind + shadcn (dark, Swiss brutalist, IBM Plex fonts)

## What's implemented (2026-02-04)
- OKF node schema (id, sensitivity, cloud_allowed, provenance, relationships)
- Auto sensitivity classification with PII regex + keyword scoring
- Data sanitization (redact / abstract / entity-replace) before cloud release
- Adaptive retrieval: vector, OKF traversal, hybrid; strategy chosen per query
- Evidence scoring: relevance, completeness, authority, diversity
- Privacy-aware router: LOCAL / CLOUD / BOTH with hard-constraint overrides
- Collaborative BOTH mode: local (private) + cloud (sanitized) + fusion
- Response validator: evidence-support, privacy-leakage, PII-in-output, citations
- Cost & latency tracking; execution trace stored per query
- Benchmark runner comparing 6 configurations across a query battery
- UI pages: Dashboard, Knowledge, Query, Traces, Privacy Audit, Benchmarks

## Backlog (P1/P2)
- OKF graph visualization (react-force-graph-2d)
- Document upload & chunking (PDF/text) with UI progress
- Streaming responses (SSE) in Query page
- Authentication / multi-user
- Real local model via Ollama on user machine (currently simulated)
