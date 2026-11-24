"""Spend cap demo, 0 API calls: a fake Claude that takes 0.5 s and costs a fixed amount.
1. 10 requests in parallel with the cap room for 3: old check (logged spend only) vs reservation.
2. Reserve vs real cost on the pipeline's Haiku calls (rows logged by scripts/s6_pipeline.py)."""
import os
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["GATEWAY_DB"] = str(Path(tempfile.mkdtemp()) / "cap.db")  # never touch the real log
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient  # noqa: E402

import gateway.proxy as proxy  # noqa: E402


class FakeUsage:
    input_tokens, output_tokens = 1000, 100
    cache_creation, cache_creation_input_tokens, cache_read_input_tokens = None, 0, 0

    def model_dump(self):
        return {}


class FakeClient:
    class messages:
        @staticmethod
        def create(**kw):
            time.sleep(0.5)
            return type("R", (), {"content": [], "usage": FakeUsage()})()


proxy._client = FakeClient()
api = TestClient(proxy.app)
BODY = {"model": "claude-sonnet-5-5", "max_tokens": 100, "guard": False}
real = proxy.cost_usd("claude-sonnet-5-5", FakeUsage())  # 1000 in + 100 out = $0.003
worst = proxy.worst_cost("claude-sonnet-5-5", None, [{"content": "x" * 2000}], 100, False)


def burst(reserve):
    proxy.reset(f"cap-{reserve}")
    proxy.db().execute("DELETE FROM log").connection.commit()
    proxy.app.state.reserve = reserve
    proxy.app.state.cap_usd = 3.5 * worst  # room for 3 worst-case calls
    send = lambda i: api.post("/v1/messages", headers={"x-tenant": "acme"},
                              json={**BODY, "messages": [{"role": "user", "content": f"{i}" + "x" * 1999}]})
    with ThreadPoolExecutor(10) as ex:
        codes = [r.status_code for r in ex.map(send, range(10))]
    spent = proxy.db().execute("SELECT SUM(cost_usd) FROM log").fetchone()[0] or 0
    print(f"reserve={'on ' if reserve else 'off'}: passed {codes.count(200)}/10, "
          f"402 {codes.count(402)}, spent ${spent:.4f} vs cap ${proxy.app.state.cap_usd:.4f} "
          f"({spent / proxy.app.state.cap_usd:.0%})")


print(f"fake call: real ${real:.4f}, reserve ${worst:.4f}")
burst(False)
burst(True)

# 2. Reserve vs real on logged pipeline rows (real DB, read only).
import sqlite3  # noqa: E402
POLICY = (ROOT / "data" / "policy.md").read_text()
SYSTEM = ("You answer customer questions for Nimbus Bikes using only the policy below. "
          "Answer in one short sentence.\n\n" + POLICY)
con = sqlite3.connect(ROOT / "results" / "gateway.db")
rows = con.execute("SELECT cost_usd, input_tokens + cache_write_tokens + cache_read_tokens FROM log"
                   " WHERE run_id LIKE 'pipeline-%' AND layer = 'claude' AND model = 'claude-haiku-5-5'"
                   ).fetchall()
w = proxy.worst_cost("claude-haiku-5-5", SYSTEM, [{"content": "x" * 60}], 60, True)
avg = sum(r[0] for r in rows) / len(rows)
print(f"\npipeline Haiku calls ({len(rows)}): real avg ${avg:.7f}, reserve ${w:.7f} = {w / avg:.1f}x; "
      f"estimated input tokens {(len(SYSTEM) + 60) / proxy.CHARS_PER_TOKEN:.0f} vs real "
      f"{sum(r[1] for r in rows) / len(rows):.0f}")
