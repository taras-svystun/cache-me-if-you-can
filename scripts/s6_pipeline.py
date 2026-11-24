"""Full pipeline demo: the 30 S1 queries plus 2 with personal data, through
guard -> exact -> semantic -> cap -> router -> Claude, against a naive gateway
(every request to Sonnet, no caches, no provider prompt caching)."""
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient  # noqa: E402

from gateway.proxy import app, db, reset, semantic_cache  # noqa: E402

POLICY = (ROOT / "data" / "policy.md").read_text()
SYSTEM = ("You answer customer questions for Nimbus Bikes using only the policy below. "
          "Answer in one short sentence.\n\n" + POLICY)
queries = json.loads((ROOT / "data" / "queries.json").read_text())
queries += [
    {"id": 31, "tenant": "acme", "kind": "pii", "q": "Please email jean.martin@example.fr his refund status."},
    {"id": 32, "tenant": "acme", "kind": "pii", "q": "Call 06 12 34 56 78 about the theft claim."},
]
semantic_cache()  # load MiniLM now, so its 2-3 s load is not billed to the first request
api = TestClient(app)


def run(name, body_extra):
    reset(f"{name}-{int(time.time())}")
    rows = []
    for q in queries:
        body = {"system": SYSTEM, "max_tokens": 60, "messages": [{"role": "user", "content": q["q"]}],
                **body_extra}
        r = api.post("/v1/messages", json=body, headers={"x-tenant": q["tenant"]})
        if r.status_code == 422:
            j = {"layer": "blocked", "cost_usd": 0.0, "latency_ms": 0.0, "trace_ms": {}, "text": ""}
        else:
            r.raise_for_status()
            j = r.json()
        rows.append({**q, **j})
    return rows


naive = run("naive", {"model": "claude-sonnet-5-5", "guard": False})
full = run("pipeline", {"model": "auto", "semantic": True, "cache_control": True})

for r in full:
    print(f'{r["id"]:>2} {r["kind"]:<10} {r["tenant"]:<4} {r["layer"]:<8} '
          f'{r.get("model", ""):<18} {r["latency_ms"]:>7.1f} ms ${r["cost_usd"]:.6f} '
          f'| {r["q"][:45]!r} -> {r["text"][:50]!r}')

print("\nlayer counts:", dict(Counter(r["layer"] for r in full)))
per_layer = defaultdict(list)
for r in full:
    for k, v in r["trace_ms"].items():
        per_layer[k].append(v)
print("median ms per layer:", {k: round(statistics.median(v), 2) for k, v in per_layer.items()})
nc, fc = sum(r["cost_usd"] for r in naive), sum(r["cost_usd"] for r in full)
nl = statistics.median(r["latency_ms"] for r in naive)
fl = statistics.median(r["latency_ms"] for r in full if r["layer"] != "blocked")
print(f"naive (all Sonnet, no caches): ${nc:.6f}, median {nl:.0f} ms, PII sent to cloud: 2")
print(f"pipeline:                      ${fc:.6f}, median {fl:.0f} ms, PII sent to cloud: "
      f"{sum(1 for r in full if r['kind'] == 'pii' and r['layer'] != 'blocked')}")
print(f"saved {1 - fc / nc:.0%}")
sem = [r for r in full if r["layer"] == "semantic"]
print("semantic hits (check each for a wrong hit):")
for r in sem:
    print(f'   {r["kind"]:<10} {r["q"]!r} -> {r["text"][:70]!r}')
print(f"total logged spend, all runs: ${db().execute('SELECT SUM(cost_usd) FROM log').fetchone()[0]:.4f}")
