# cache-me-if-you-can: plan

Why and what matters: `BRIEF.md`. What we measured: `journal.md`.

## What we build
FastAPI proxy: client -> proxy -> Claude, run in-process with TestClient. Every request is a row
in a SQLite cost log (model, tokens, cost, cache hit, latency). Models: `claude-haiku-5-5`
(default, cheap route), `claude-sonnet-5-5` (hard route).

## Rules
- Each step: Taras guesses -> Claude builds -> measure -> checkpoint -> commit.
  Taras writes only the one-line key pieces (exact-cache key, SQL query).
- Budget $3 (Console workspace limit). Proxy returns HTTP 402 once logged cost passes $2.50.
- Test data made up: ~30 queries (exact repeats, paraphrases, traps) and a made-up policy document.
- Every step adds one row to a single results table from Taras's SQL query:
  hit rate, wrong-hit rate, $ saved, ms added.
- Out: Ollama, sandbox change for localhost, phone part. Repo private until after the call.

## Steps, in priority order
Work down the list until time runs out. 2026-11-24, Taras's call: breadth first, a thin slice
of every step (S1 30 min, S3 20, S2 25, S4 20, S5 15), then go deeper in the time left.

- ✅ S0 Setup: files, venv, Gemma download, critic run.
- ✅ S0.5 Smoke test: one Haiku call (max_tokens=5) with the `SSL_CERT_FILE` fix;
  `models.list` shows both model IDs.
- ✅ S1 Proxy + cost log + exact cache + SQL. Cost counts `cache_creation_input_tokens` and
  `cache_read_input_tokens` from the start. Cache key: model, system, temperature, tenant,
  normalised messages (whitespace only, no lowercase: Taras's call, case can carry meaning, e.g.
  policy IDs). Check: repeat is a hit with 0 tokens and ~0 ms; tenants never share a hit;
  hit rate on the query set; SQL gives cost per model; 402 fires with a lowered cap.
- [ ] S3 Provider prompt caching. First read Anthropic's docs for minimum cacheable length and
  prices (cite page and date). Check: second call has `cache_read_input_tokens` > 0 and the cost
  drop matches the docs.
- [ ] S2 Semantic cache, `sentence-transformers` on CPU. Check: hit rate and wrong hits at 3+
  thresholds; the "policy 2024 vs 2025" wrong hit shown, and one way to block it.
- [ ] S4 Router: Haiku for simple, Sonnet for hard. Check on ~10 tasks: route, quality (Taras
  judges; a stated limit, not a result), cost saved against all-Sonnet.
- [ ] S5 Local guard, 40-minute timebox. Gemma in Taras's terminal (`scripts/gemma_guard.py`,
  README), regex side and comparison by Claude. Check: what each catches, seconds each adds.
  First fix the thinking problem (journal).

## Time
2026-11-24: call at 13:00, stop at 12:30. Mock interview 12:15-12:30 in a fresh session (sees
only the journal and the call prep), whatever step we are on. Undone steps go to Later.

## Later
- S6 Streaming. Line for the call: token counts arrive in the final stream event, so the log row
  is written when the stream closes.
