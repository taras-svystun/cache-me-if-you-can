# cache-me-if-you-can: plan

## Purpose
Taras has a technical call with TheTop's FDE engineer on 2026-11-24. TheTop's product, TheEngine,
is a gateway between a company and its AI providers: routing, caching, policy checks, spend
dashboard. His gaps: caching layers, routing, SQL basics, local AI. Tonight he builds a tiny
gateway and measures it, so tomorrow he can say "I measured this yesterday", not "I would do it
like this". Call prep: `ai-job-search/documents/applications/thetop_applied_ai_engineer_fde/interview_prep_fde_call.md`.

## What we build
A FastAPI proxy: client -> proxy -> Claude. Every request goes into a SQLite cost log
(model, tokens, cost, cache hit, latency). Demos run in-process with FastAPI TestClient.
Models: Haiku 5.5 (`claude-haiku-5-5`) as the default and cheap route, Sonnet 5.5
(`claude-sonnet-5-5`) as the hard route.

## Decided
- Understanding over typing: Claude builds; Taras guesses each result before we measure, and
  writes only the one-line key pieces (the exact-cache key, the SQL query).
- One session per step; `/clear` between steps. Each new session starts from this plan and the journal.
- Budget $3: a new Anthropic key in its own workspace with a $3 limit in the Console, pasted
  into `.env` by Taras with `read -s`. Spend cap in code: HTTP 402 over $2.50 logged.
- Subagents: the critic once on this plan (prompt in `docs/critic.md`), and web-fetch to read
  Anthropic docs. Both run on the Claude Code subscription, not on the API budget.
- Test data made up by Claude: about 30 queries with exact repeats, paraphrases and traps;
  a made-up company policy as the long document.
- Git: Taras ran `git init` and the remote (private repo). Claude gives a commit command per step.
- Mock interview in a fresh session that sees only the journal and the call prep file.
- Against: no Ollama server, no sandbox change for localhost, no phone part, repo stays private
  until after the call.

## Steps
Each step: Taras guesses -> Claude builds -> measure -> checkpoint -> commit -> `/clear`.

- ✅ S0 Setup: project files, venv, model download started, plan, critic.
  Check: files exist, critic's changes folded in.
- [ ] S0.5 Smoke test, 10 min (from the critic: riskiest assumption is that the toolchain works in
  the sandbox). Check: one `claude-haiku-5-5` call with max_tokens=5 through the `SSL_CERT_FILE`
  fix, and `models.list` shows both model IDs. Gemma half done 2026-11-23: inside the sandbox MLX
  fails with "No Metal device available", so Gemma runs in Taras's terminal (see S5). Still to see:
  Taras's first run of `scripts/gemma_guard.py` (does mlx-lm support Gemma 4).
- [ ] S1 Proxy, cost log, exact cache, SQL. The cost formula counts `cache_creation_input_tokens`
  and `cache_read_input_tokens` from the start, else the cap and S3 are wrong. The cache key holds
  model, system prompt, temperature, tenant and the normalised messages. Check: a repeated request
  is a hit with 0 tokens and ~0 ms; two tenants never share a hit; hit rate on the query set;
  Taras's SQL query gives cost per model; 402 fires over the cap (test with a lowered cap).

Every step ends with one row in a single results table (hit rate, wrong-hit rate, $ saved, ms
added), produced by Taras's SQL query: one table to recite in the call.
- [ ] S3 Provider prompt caching. First read Anthropic's docs for the current minimum cacheable
  length and cache prices (cite page and date in the journal). Check: second call shows
  `cache_read_input_tokens` > 0 and the measured cost drop matches the docs.
- [ ] S2 Semantic cache with `sentence-transformers` embeddings on CPU (`device="cpu"`: the sandbox
  hides the GPU). Check: hit rate and wrong hits across 3+ thresholds; the "policy 2024 vs 2025"
  wrong hit shown, and one way to block it.
- [ ] S4 Router: Haiku for simple, Sonnet for hard. Check: on ~10 tasks, route chosen, answer
  quality (Taras judges), cost saved against all-Sonnet. Quality on 10 tasks judged by one person
  is a stated limit, not a result.
- [ ] S7 Mock interview, 15 minutes, fresh session. Check: Taras answers each question with a number
  he measured.
- [ ] S5 Local guard, 40-minute timebox, only if time is left. Gemma runs in Taras's own terminal
  (`scripts/gemma_guard.py`, command in README): the sandbox hides Metal from MLX. Claude adds the
  regex side and the comparison. Check: a table of what each catches and the seconds each adds.

## Time
Decided 2026-11-23 23:00: Taras sleeps now; the call is 2026-11-24 at 12:00. Work resumes in the
morning; hard stop 11:00 to rest before the call. Steps not done by then go to Later.

## Later
- S6 Streaming: cut by the critic, no step depends on it. Say in the call: token counts arrive in
  the final stream event, so the log row is written when the stream closes.
