"""S1 demo: run the 30-query set through the proxy (in-process), then measure the exact cache.

Prints: one line per query, hit rate, hit vs miss latency, cost per model (SQL), 402 check.
"""
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient  # noqa: E402

from gateway.proxy import app, db  # noqa: E402

SYSTEM = ("You answer customer questions for Nimbus Bikes, a made-up e-bike shop. "
          "Answer in one short sentence. If you do not know, say so.")

COST_PER_MODEL_SQL = """
SELECT model, COUNT(*) AS calls, SUM(cache_hit) AS hits, ROUND(SUM(cost_usd), 6) AS cost_usd
FROM log WHERE run_id = ? GROUP BY model
"""

run_id = f"s1-{int(time.time())}"
app.state.run_id = run_id
con = db()
con.execute("DELETE FROM exact_cache")  # every run starts with a cold cache
con.commit()

api = TestClient(app)
queries = json.loads((ROOT / "data" / "queries.json").read_text())
rows = []
for q in queries:
    body = {"system": SYSTEM, "max_tokens": 60, "messages": [{"role": "user", "content": q["q"]}]}
    r = api.post("/v1/messages", json=body, headers={"x-tenant": q["tenant"]}).json()
    rows.append({**q, **r})
    print(f'{q["id"]:>2} {q["kind"]:<10} {q["tenant"]:<4} {"HIT " if r["cache_hit"] else "miss"} '
          f'{r["latency_ms"]:>8.1f} ms  ${r["cost_usd"]:.6f}  {r["text"][:60]!r}')

hits = [r for r in rows if r["cache_hit"]]
miss = [r for r in rows if not r["cache_hit"]]
print(f"\nhit rate: {len(hits)}/{len(rows)} = {len(hits) / len(rows):.1%}")
print("hits by kind:", {k: sum(r["cache_hit"] for r in rows if r["kind"] == k)
                        for k in dict.fromkeys(r["kind"] for r in rows)})
print(f"median latency: hit {statistics.median(r['latency_ms'] for r in hits):.2f} ms, "
      f"miss {statistics.median(r['latency_ms'] for r in miss):.0f} ms")
saved = statistics.mean(r["cost_usd"] for r in miss) * len(hits)
print(f"$ saved by hits (avg miss cost x hits): ${saved:.6f}")

print("\ncost per model (SQL):")
for row in con.execute(COST_PER_MODEL_SQL, (run_id,)):
    print("  ", row)

# 402: lower the cap below what is already spent, then send a query that is not cached.
app.state.cap_usd = 0.000001
body = {"system": SYSTEM, "max_tokens": 60, "messages": [{"role": "user", "content": "A new question."}]}
r = api.post("/v1/messages", json=body, headers={"x-tenant": "acme"})
print(f"\n402 check (cap $0.000001, uncached query): HTTP {r.status_code} {r.json()}")
body["messages"][0]["content"] = queries[0]["q"]
r = api.post("/v1/messages", json=body, headers={"x-tenant": "acme"})
print(f"same cap, cached query: HTTP {r.status_code} hit={r.json().get('cache_hit')}")
total = con.execute("SELECT SUM(cost_usd) FROM log").fetchone()[0]
print(f"\ntotal logged spend, all runs: ${total:.6f}")
