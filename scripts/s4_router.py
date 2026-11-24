"""S4 demo: route 10 tasks, compare cost with all-Sonnet. Each task runs on both models so
Taras can judge whether Haiku's answer is good enough where it was routed.
Writes all answers to results/router_answers.md."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient  # noqa: E402

from gateway.proxy import app, client, cost_usd, reset  # noqa: E402
from gateway.router import HAIKU, SONNET, route_haiku, route_rules  # noqa: E402

POLICY = (ROOT / "data" / "policy.md").read_text()
SYSTEM = ("You answer customer questions for Nimbus Bikes using only the policy below. "
          "Be brief: at most 4 sentences.\n\n" + POLICY)
con = reset(f"s4-{int(time.time())}")
api = TestClient(app)
tasks = json.loads((ROOT / "data" / "router_tasks.json").read_text())

out, rows = ["# S4 router answers (made-up policy)\n"], []
for t in tasks:
    ans = {}
    for m in (HAIKU, SONNET):
        body = {"model": m, "system": SYSTEM, "max_tokens": 300, "cache_control": True,
                "messages": [{"role": "user", "content": t["q"]}]}
        ans[m] = api.post("/v1/messages", json=body, headers={"x-tenant": "acme"}).json()
    t0 = time.perf_counter()
    rh, u = route_haiku(t["q"], client())
    router_ms = (time.perf_counter() - t0) * 1000
    rows.append(dict(t, rules=route_rules(t["q"]), haiku=rh, router_cost=cost_usd(HAIKU, u),
                     router_ms=router_ms, cost={m: ans[m]["cost_usd"] for m in ans},
                     ms={m: ans[m]["latency_ms"] for m in ans}))
    out.append(f"## {t['id']} ({t['level']}) {t['q']}\n\n**Haiku:** {ans[HAIKU]['text']}\n\n"
               f"**Sonnet:** {ans[SONNET]['text']}\n")
    short = lambda m: "H" if m == HAIKU else "S"
    print(f"{t['id']:>2} {t['level']:<6} rules={short(rows[-1]['rules'])} haiku-router={short(rh)} "
          f"H ${ans[HAIKU]['cost_usd']:.6f} {ans[HAIKU]['latency_ms']:.0f} ms | "
          f"S ${ans[SONNET]['cost_usd']:.6f} {ans[SONNET]['latency_ms']:.0f} ms | "
          f"router {router_ms:.0f} ms")

(ROOT / "results" / "router_answers.md").write_text("\n".join(out))
all_s = sum(r["cost"][SONNET] for r in rows)
ideal = sum(r["cost"][HAIKU if r["level"] == "simple" else SONNET] for r in rows)
rules = sum(r["cost"][r["rules"]] for r in rows)
hk = sum(r["cost"][r["haiku"]] + r["router_cost"] for r in rows)
print(f"\nall-Sonnet ${all_s:.6f}")
for name, c in (("perfect routes", ideal), ("rules router", rules), ("haiku router (incl. its calls)", hk)):
    print(f"{name:<31} ${c:.6f}  saved {1 - c / all_s:.0%}")
print(f"router calls total ${sum(r['router_cost'] for r in rows):.6f}, "
      f"median {sorted(r['router_ms'] for r in rows)[5]:.0f} ms")
mis = lambda k: [r["id"] for r in rows if (r[k] == HAIKU) != (r["level"] == "simple")]
print("misroutes: rules", mis("rules"), "| haiku", mis("haiku"))
print(f"total logged spend, all runs: ${con.execute('SELECT SUM(cost_usd) FROM log').fetchone()[0]:.4f}")
