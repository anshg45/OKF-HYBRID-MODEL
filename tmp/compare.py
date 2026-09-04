import requests, json, time

API = "http://localhost:8001/api"

# Test queries
PRIVATE_Q = "What is our employee compensation policy including specific amounts?"
MIXED_Q = "Compare our company compensation with current industry trends."
PUBLIC_Q = "How does RAG reduce hallucination?"

def run(query, mode, label):
    t0 = time.time()
    r = requests.post(f"{API}/query", json={"query": query, "mode": mode}, timeout=90).json()
    elapsed = time.time() - t0
    return {
        "label": label,
        "mode_used": r.get("execution_mode"),
        "cost": r.get("cost", 0),
        "latency_ms": r.get("latency_ms", 0),
        "evidence": r.get("evidence_quality", {}).get("score", 0),
        "validation_ok": r.get("validation", {}).get("passed", False),
        "checks": {c["name"]: c["passed"] for c in r.get("validation", {}).get("checks", [])},
        "n_sources": len(r.get("sources_used", [])),
        "n_sanitized": len([s for s in r.get("sources_used", []) if s.get("sanitized")]),
        "cloud_released": len(r.get("cloud_release_log") or []),
        "routing_reasons": r.get("routing", {}).get("reasons", []),
        "privacy_exposure": r.get("routing", {}).get("estimated_privacy_exposure", 0),
        "answer": (r.get("final_answer") or "")[:220],
    }

def print_row(res):
    print(f"  {res['label']:<38} mode={res['mode_used']:<5} "
          f"cost=${res['cost']:.6f}  lat={res['latency_ms']:>5}ms  "
          f"exposure={res['privacy_exposure']:.2f}  "
          f"privacy_ok={'✓' if res['checks'].get('privacy_leakage') else '✗'}  "
          f"leak_ok={'✓' if res['checks'].get('no_pii_in_output') else '✗'}  "
          f"sanitized={res['n_sanitized']}/{res['n_sources']}")

def scenario(name, q, modes):
    print(f"\n{'='*95}\n[{name}]  Q: {q}\n{'='*95}")
    results = []
    for label, mode in modes:
        r = run(q, mode, label)
        results.append(r)
        print_row(r)
    return results

# Scenario 1: private query (compensation) — everything must stay local ideally
r1 = scenario("SCENARIO 1 · PRIVATE-ONLY QUERY", PRIVATE_Q, [
    ("Plain Cloud (forced)", "cloud"),
    ("Plain Local", "local"),
    ("Our AUTO router", "auto"),
])

# Scenario 2: mixed (private + public)
r2 = scenario("SCENARIO 2 · MIXED-SENSITIVITY QUERY", MIXED_Q, [
    ("Plain Cloud (forced)", "cloud"),
    ("Plain Local", "local"),
    ("Our BOTH (collaborative)", "both"),
    ("Our AUTO router", "auto"),
])

# Scenario 3: pure public knowledge
r3 = scenario("SCENARIO 3 · PUBLIC-ONLY QUERY", PUBLIC_Q, [
    ("Plain Cloud", "cloud"),
    ("Plain Local", "local"),
    ("Our AUTO router", "auto"),
])

# --- summary ---
print(f"\n{'#'*95}\n# SIDE-BY-SIDE SUMMARY (average across the 3 scenarios above)\n{'#'*95}\n")

def agg(results_list, mode_label):
    picks = []
    for scen in results_list:
        for r in scen:
            if r["label"] == mode_label or (mode_label in r["label"]):
                picks.append(r); break
    if not picks: return None
    return {
        "n": len(picks),
        "avg_cost": sum(p["cost"] for p in picks)/len(picks),
        "avg_latency": sum(p["latency_ms"] for p in picks)/len(picks),
        "privacy_pass": sum(1 for p in picks if p["checks"].get("privacy_leakage"))/len(picks),
        "leak_pass": sum(1 for p in picks if p["checks"].get("no_pii_in_output"))/len(picks),
        "avg_exposure": sum(p["privacy_exposure"] for p in picks)/len(picks),
    }

configs = ["Plain Cloud", "Plain Local", "Our AUTO"]
scen_all = [r1, r2, r3]
print(f"{'CONFIG':<20} {'COST':>10} {'LAT':>8} {'PRIVACY_LEAK_OK':>18} {'NO_PII_OUT':>12} {'EXPOSURE':>10}")
print("-"*82)
for c in configs:
    a = agg(scen_all, c)
    if a:
        print(f"{c:<20} ${a['avg_cost']:>8.6f} {a['avg_latency']:>6.0f}ms "
              f"{a['privacy_pass']*100:>14.0f}%   {a['leak_pass']*100:>10.0f}%   {a['avg_exposure']:>10.2f}")

# Cost savings
plain_cloud = agg(scen_all, "Plain Cloud")
our_auto = agg(scen_all, "Our AUTO")
plain_local = agg(scen_all, "Plain Local")

print("\n--- KEY TAKEAWAYS ---")
if plain_cloud and our_auto:
    savings = (1 - our_auto["avg_cost"]/plain_cloud["avg_cost"]) * 100
    print(f"vs Plain Cloud: our AUTO is {savings:.1f}% cheaper (${plain_cloud['avg_cost']:.6f} → ${our_auto['avg_cost']:.6f})")
if plain_local and our_auto:
    cost_delta = our_auto["avg_cost"] / plain_local["avg_cost"] if plain_local["avg_cost"] else 0
    print(f"vs Plain Local: AUTO costs {cost_delta:.1f}× more but gets cloud-quality answers when safe")
if plain_cloud and our_auto:
    print(f"Privacy exposure: Plain Cloud={plain_cloud['avg_exposure']:.2f} vs AUTO={our_auto['avg_exposure']:.2f}")
    print(f"Privacy leak-check pass rate: Plain Cloud={plain_cloud['privacy_pass']*100:.0f}% vs AUTO={our_auto['privacy_pass']*100:.0f}%")

# save
json.dump({"scenario1": r1, "scenario2": r2, "scenario3": r3},
          open("/app/tmp/comparison.json","w"), indent=2, default=str)
print("\n(saved /app/tmp/comparison.json)")
