"""The gateway: a FastAPI proxy in front of Claude.

One endpoint, POST /v1/messages. For each request:
1. build the exact-cache key; on a hit, return the stored answer (0 tokens, no Claude call);
2. on a miss, refuse with 402 if the logged cost already passed the spend cap;
3. call Claude, store the answer under the key, write one cost-log row.
"""
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path

import anthropic
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("GATEWAY_DB", ROOT / "results" / "gateway.db"))

# USD per million tokens. Source: claude-api skill model table and prompt-caching
# economics (cached 2026-11-03). S3 checks these against the live pricing page.
# Cache writes: 1.25x input (5-minute TTL), 2x input (1-hour TTL).
PRICES = {
    "claude-haiku-5-5": dict(input=0.10, output=0.50, write_5m=0.125, write_1h=0.20, read=0.01),
    "claude-sonnet-5-5": dict(input=2.00, output=10.00, write_5m=2.50, write_1h=4.00, read=0.10),
}

# Thinking off, so short answers stay short and cheap. Haiku 5.5 accepts "disabled";
# Sonnet 5.5 rejects it and uses "between_tools" instead.
THINKING = {
    "claude-haiku-5-5": {"type": "disabled"},
    "claude-sonnet-5-5": {"type": "between_tools"},
}


def load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def normalise(text: str) -> str:
    """Collapse runs of whitespace and trim. No lowercasing: case can carry meaning (AB12 vs Ab12)."""
    return " ".join(text.split())


def cache_key(model, system, max_tokens, tenant, messages) -> str:
    msgs = [(m["role"], normalise(m["content"])) for m in messages]
    blob = json.dumps([model, normalise(system or ""), max_tokens, tenant, msgs])
    return hashlib.sha256(blob.encode()).hexdigest()


def cost_usd(model: str, usage) -> float:
    """Cost of one call. input_tokens excludes cached tokens, so the four parts add up."""
    p = PRICES[model]
    cc = usage.cache_creation
    w5 = cc.ephemeral_5m_input_tokens if cc else (usage.cache_creation_input_tokens or 0)
    w1 = cc.ephemeral_1h_input_tokens if cc else 0
    tokens = dict(input=usage.input_tokens, output=usage.output_tokens,
                  write_5m=w5, write_1h=w1, read=usage.cache_read_input_tokens or 0)
    return sum(tokens[k] * p[k] for k in tokens) / 1e6


def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript("""
    CREATE TABLE IF NOT EXISTS log (
        id INTEGER PRIMARY KEY, ts REAL, run_id TEXT, tenant TEXT, model TEXT,
        input_tokens INT, output_tokens INT, cache_write_tokens INT, cache_read_tokens INT,
        cost_usd REAL, cache_hit INT, latency_ms REAL);
    CREATE TABLE IF NOT EXISTS exact_cache (key TEXT PRIMARY KEY, response TEXT);
    """)
    return con


class Req(BaseModel):
    model: str = "claude-haiku-5-5"
    system: str | None = None
    messages: list[dict]
    max_tokens: int = 100
    cache_control: bool = False  # S3: ask the provider to cache the prompt prefix


app = FastAPI()
app.state.cap_usd = float(os.environ.get("SPEND_CAP_USD", "2.50"))
app.state.run_id = "dev"
_client = None


def client():
    global _client
    if _client is None:
        load_env()
        _client = anthropic.Anthropic()
    return _client


@app.post("/v1/messages")
def messages(req: Req, x_tenant: str = Header(...)):
    t0 = time.perf_counter()
    con = db()
    key = cache_key(req.model, req.system, req.max_tokens, x_tenant, req.messages)

    row = con.execute("SELECT response FROM exact_cache WHERE key=?", (key,)).fetchone()
    if row:
        ms = (time.perf_counter() - t0) * 1000
        log(con, x_tenant, req.model, 0, 0, 0, 0, 0.0, 1, ms)
        return {**json.loads(row[0]), "cache_hit": True, "cost_usd": 0.0, "latency_ms": ms}

    # Checked after the cache: a hit costs nothing, so it is served even over the cap.
    spent = con.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM log").fetchone()[0]
    if spent >= app.state.cap_usd:
        raise HTTPException(402, f"spend cap reached: ${spent:.4f} >= ${app.state.cap_usd:.2f}")

    kwargs = dict(model=req.model, max_tokens=req.max_tokens, messages=req.messages,
                  thinking=THINKING[req.model])
    if req.system:
        kwargs["system"] = req.system
    if req.cache_control:
        kwargs["cache_control"] = {"type": "ephemeral"}
    r = client().messages.create(**kwargs)

    text = "".join(b.text for b in r.content if b.type == "text")
    u = r.usage
    cost = cost_usd(req.model, u)
    ms = (time.perf_counter() - t0) * 1000
    con.execute("INSERT OR REPLACE INTO exact_cache VALUES (?, ?)", (key, json.dumps({"text": text})))
    log(con, x_tenant, req.model, u.input_tokens, u.output_tokens,
        u.cache_creation_input_tokens or 0, u.cache_read_input_tokens or 0, cost, 0, ms)
    return {"text": text, "cache_hit": False, "cost_usd": cost, "latency_ms": ms,
            "usage": u.model_dump()}


def log(con, tenant, model, inp, out, cw, cr, cost, hit, ms):
    con.execute("INSERT INTO log (ts, run_id, tenant, model, input_tokens, output_tokens,"
                " cache_write_tokens, cache_read_tokens, cost_usd, cache_hit, latency_ms)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (time.time(), app.state.run_id, tenant, model, inp, out, cw, cr, cost, hit, ms))
    con.commit()
