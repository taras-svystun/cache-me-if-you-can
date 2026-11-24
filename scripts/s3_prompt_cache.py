"""S3 demo: provider prompt caching. The policy document goes in the system prompt with a
cache_control breakpoint; several different questions reuse it.

Calls: A writes the cache, B and C read it, D is the same question as B with caching off
(baseline). E and F use a short system prompt (under 512 tokens) to show it silently never caches.
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient  # noqa: E402

from gateway.proxy import PRICES, app, db  # noqa: E402

POLICY = (ROOT / "data" / "policy.md").read_text()
SYSTEM = ("You answer customer questions for Nimbus Bikes using only the policy below. "
          "Answer in one short sentence.\n\n" + POLICY)
SHORT = "You answer customer questions for Nimbus Bikes, a made-up e-bike shop. One sentence."

app.state.run_id = f"s3-{int(time.time())}"
con = db()
con.execute("DELETE FROM exact_cache")
con.commit()
api = TestClient(app)

calls = [
    ("A write", SYSTEM, True, "Does the warranty cover a flat tyre?"),
    ("B read", SYSTEM, True, "What is the return window for an e-bike?"),
    ("C read", SYSTEM, True, "What does policy AB12 say about theft?"),
    ("D no cache", SYSTEM, False, "What is the return window for an e-bike? (baseline)"),
    ("E short", SHORT, True, "Is there a student discount?"),
    ("F short", SHORT, True, "How do I reset the display?"),
]
p = PRICES["claude-haiku-5-5"]
for name, system, cc, q in calls:
    body = {"system": system, "max_tokens": 60, "cache_control": cc,
            "messages": [{"role": "user", "content": q}]}
    r = api.post("/v1/messages", json=body, headers={"x-tenant": "acme"}).json()
    u = r["usage"]
    inp_cost = (u["input_tokens"] * p["input"] + (u["cache_creation_input_tokens"] or 0) * p["write_5m"]
                + (u["cache_read_input_tokens"] or 0) * p["read"]) / 1e6
    print(f"{name:<11} input={u['input_tokens']:>5} write={u['cache_creation_input_tokens'] or 0:>5} "
          f"read={u['cache_read_input_tokens'] or 0:>5} out={u['output_tokens']:>3} "
          f"input_cost=${inp_cost:.7f} total=${r['cost_usd']:.7f} {r['latency_ms']:>6.0f} ms "
          f"| {r['text'][:70]!r}")
