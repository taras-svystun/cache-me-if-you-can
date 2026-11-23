# cache-me-if-you-can: brief

Written 2026-11-23 in the ai-job-search session, after a grilling round with Taras.
Read this first, then run the `new-project` skill (fold this brief into PLAN.md and journal).

## Why
Taras has a technical call with TheTop's FDE engineer on 2026-11-24. TheTop's product,
TheEngine, is a gateway between a company and its AI providers: routing, caching, policy checks,
spend dashboard. His gaps: caching layers (never built one), routing, SQL basics, local AI.
Goal tonight: understand the mechanisms by building a tiny gateway and measuring it, so tomorrow
he says "I measured this yesterday", not "I would do it like this".

## How we work (decided)
- Understanding over typing. Claude Code builds. Before each demo Taras guesses the result,
  then we measure. Taras writes code only where one line gives 90% of the understanding
  (for example the exact-cache key, the SQL query): he tries, Claude corrects, move on.
- Plain explanations of each mechanism, with where it stops working.
- Checkpoint after each priority; Taras decides whether to go on. No hard time limit.
- Budget: $2-3 of Anthropic tokens. Taras's own key in `.env` (gitignored, never committed).
  Do not use the `OPENAI_API_KEY` in the shell: owner unknown, may be a client's.

## What we build, in priority order
A FastAPI proxy: client -> proxy -> Claude. Every request logged to SQLite (model, tokens,
cost, cache hit, latency). Demos run in-process with FastAPI TestClient: no open port.
- P1: three cache levels, plus the cost log and a SQL query on it.
  1. Exact cache: hash of the normalised request. Measure the hit rate.
  2. Semantic cache: local embeddings (`sentence-transformers`), tune a similarity threshold,
     catch a wrong hit ("policy 2024" vs "policy 2025").
  3. Provider prompt caching: a long document first in the prompt; read
     `cache_read_input_tokens` and the price change. Check the current minimum cacheable
     length and prices in Anthropic's docs first.
- P2: router. Simple tasks to Haiku, hard to Sonnet; check quality on ~10 tasks.
- P3: local guard. Gemma 4 E4B 4-bit on MLX (`mlx-community/gemma-4-e4b-it-4bit`, 5.18 GB,
  checked 2026-11-23), run in-process, checks a request for personal data before it goes to the
  cloud. Compare with regex on ~10 examples: what each catches, the seconds it adds.
  `HF_HOME=./.cache` (gitignored); dont-paste-that reuses this cache.
- P4: streaming through the proxy, if time allows.
- End: a 15-minute mock interview on what we built.

## Decided against
- No Ollama server and no sandbox change for localhost: MLX in-process is simpler and safer.
- No phone part tonight: it stays in dont-paste-that.
- Keep the repo private until after the call; Taras decides on publishing.

## Related
`~/Documents/Projects/dont-paste-that/docs/PLAN.md` reuses this proxy later.
TheEngine facts and call prep: `ai-job-search/documents/applications/thetop_applied_ai_engineer_fde/interview_prep_fde_call.md`.
