"""The gateway: a FastAPI proxy in front of Claude.

One endpoint, POST /v1/messages. Pipeline, cheapest and safest first:
guard -> exact cache -> semantic cache -> spend cap -> router -> Claude.
Each layer only sees what the layers before it let through; every request writes one cost-log row.
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

from gateway.guard import scan
from gateway.router import route_rules

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("GATEWAY_DB", ROOT / "results" / "gateway.db"))

# USD per million tokens. Checked 2026-11-24 against platform.claude.com pricing page.
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
        cost_usd REAL, cache_hit INT, latency_ms REAL, layer TEXT);
    CREATE TABLE IF NOT EXISTS exact_cache (key TEXT PRIMARY KEY, response TEXT);
    """)
    return con


def reset(run_id: str) -> sqlite3.Connection:
    """Start a demo run: new run_id, empty exact cache, empty semantic cache (if loaded)."""
    app.state.run_id = run_id
    con = db()
    con.execute("DELETE FROM exact_cache")
    con.commit()
    if _semantic is not None:
        _semantic.entries.clear()
    return con


class Req(BaseModel):
    model: str = "claude-haiku-5-5"  # "auto": the router picks Haiku or Sonnet
    system: str | None = None
    messages: list[dict]
    max_tokens: int = 100
    cache_control: bool = False  # S3: ask the provider to cache the prompt prefix
    guard: bool = True  # S5: regex PII check, blocks with 422 before anything stores or sends it
    semantic: bool = False  # S2: semantic cache after the exact cache (loads MiniLM on first use)
    semantic_threshold: float = 0.90


app = FastAPI()
app.state.cap_usd = float(os.environ.get("SPEND_CAP_USD", "2.50"))
app.state.run_id = "dev"
_client = None
_semantic = None


def client():
    global _client
    if _client is None:
        load_env()
        _client = anthropic.Anthropic()
    return _client


def semantic_cache():
    global _semantic
    if _semantic is None:
        from gateway.semantic import SemanticCache
        _semantic = SemanticCache()
    return _semantic


@app.post("/v1/messages")
def messages(req: Req, x_tenant: str = Header(...)):
    t0 = time.perf_counter()
    trace = {}

    def lap(name):
        nonlocal t0
        now = time.perf_counter()
        trace[name] = round((now - t0) * 1000, 3)
        t0 = now

    def done(layer, text, cost=0.0, model=req.model, usage=None, toks=(0, 0, 0, 0)):
        total, hit = sum(trace.values()), layer in ("exact", "semantic")
        con.execute("INSERT INTO log (ts, run_id, tenant, model, input_tokens, output_tokens,"
                    " cache_write_tokens, cache_read_tokens, cost_usd, cache_hit, latency_ms, layer)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (time.time(), app.state.run_id, x_tenant, model, *toks, cost, int(hit), total, layer))
        con.commit()
        out = {"text": text, "layer": layer, "model": model, "cache_hit": hit,
               "cost_usd": cost, "latency_ms": total, "trace_ms": trace}
        return {**out, "usage": usage} if usage else out

    con = db()
    question = req.messages[-1]["content"]

    # 1. Guard first: every later layer stores the prompt (caches, log) or sends it out (Claude).
    if req.guard:
        # User messages only: the system prompt is the operator's own text (the policy holds a
        # public service email on purpose), so scanning it blocked every request.
        found = scan(" ".join(m["content"] for m in req.messages if m["role"] == "user"))
        lap("guard")
        if found:
            done("blocked", "")
            raise HTTPException(422, f"personal data found: {found}")

    # 2. Exact cache: ~0.6 ms, never wrong for the same key.
    key = cache_key(req.model, req.system, req.max_tokens, x_tenant, req.messages)
    row = con.execute("SELECT response FROM exact_cache WHERE key=?", (key,)).fetchone()
    lap("exact")
    if row:
        return done("exact", json.loads(row[0])["text"])

    # 3. Semantic cache: ~8 ms, can be wrong. Scoped by tenant AND by everything else in the key
    # except the question, so a different system prompt or model never shares an answer.
    scope = cache_key(req.model, req.system, req.max_tokens, x_tenant, req.messages[:-1])
    if req.semantic and len(req.messages) == 1:
        hit = semantic_cache().get(scope, question, req.semantic_threshold)
        lap("semantic")
        if hit is not None:
            return done("semantic", hit)

    # 4. Spend cap. After the caches: a hit costs nothing, so it is served even over the cap.
    spent = con.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM log").fetchone()[0]
    if spent >= app.state.cap_usd:
        raise HTTPException(402, f"spend cap reached: ${spent:.4f} >= ${app.state.cap_usd:.2f}")

    # 5. Router: only requests that will really call a model get routed.
    model = req.model
    if model == "auto":
        model = route_rules(question)
        lap("router")

    # 6. Claude.
    kwargs = dict(model=model, max_tokens=req.max_tokens, messages=req.messages,
                  thinking=THINKING[model])
    if req.system and req.cache_control:
        # Breakpoint on the system block: the shared document is the prefix to reuse.
        # (A top-level marker would land on the last message, so the question would be in
        # the cached prefix and the next, different question would miss.)
        kwargs["system"] = [{"type": "text", "text": req.system,
                             "cache_control": {"type": "ephemeral"}}]
    elif req.system:
        kwargs["system"] = req.system
    r = client().messages.create(**kwargs)
    lap("claude")

    text = "".join(b.text for b in r.content if b.type == "text")
    u = r.usage
    con.execute("INSERT OR REPLACE INTO exact_cache VALUES (?, ?)", (key, json.dumps({"text": text})))
    if req.semantic and len(req.messages) == 1:
        semantic_cache().put(scope, question, text)
    lap("store")
    return done("claude", text, cost_usd(model, u), model, u.model_dump(),
                (u.input_tokens, u.output_tokens, u.cache_creation_input_tokens or 0,
                 u.cache_read_input_tokens or 0))

