# Journal

Newest at the bottom.

## 2026-11-23 · S0 setup
- Brief written in the ai-job-search session; grilled again here. Decisions are in `PLAN.md`.
- `.gitignore`, empty `.env` (mode 600), `.venv` with `huggingface_hub` 2.4.0.
- Research verdict: Python HTTPS fails in the sandbox with `OSStatus -26276`. Cause: `httpcore2`
  verifies TLS through `truststore`, which asks the macOS trust service, which the sandbox blocks.
  Evidence: curl to huggingface.co returns 200; Python fails at `start_tls`. Fix: `SSL_CERT_FILE`
  (read first in `httpcore2/_ssl.py:21`) pointed at pip's bundled `cacert.pem`. Small files then download.
- Research verdict: Gemma weight download via xet (`cas-server.xethub.hf.co`) fails the same way,
  probably the same TLS cause (not proven). `HF_HUB_DISABLE_XET=1` worked: 4.8 GiB in `.cache`.
- Git: the sandbox blocks writing `.git`. Taras runs `git init`, the remote and each commit.
- Deps installed: anthropic 2.13.0, fastapi 0.165.0, mlx 0.32.4, mlx-lm 0.32.2,
  sentence-transformers 6.3.0, torch 2.15.0, transformers 5.24.0.
- Critic run on the plan. Taken: smoke test first, cost formula with cache tokens in S1, tenant in
  the cache key, one results table. Taras agreed: cut S6, reorder S1 -> S3 -> S2 -> S4 -> S7 -> S5.
- Research verdict: MLX cannot run inside the Claude Code sandbox. `import mlx.core` fails with
  "[metal::load_device] No Metal device available"; no CPU switch found in MLX's env vars.
  So Gemma runs in Taras's own terminal via `scripts/gemma_guard.py`. Torch for embeddings
  runs on CPU here. Checked offline: the Gemma chat template loads (`<|turn>user ... <|turn>model`)
  and the script compiles; the model run itself is not yet verified.
- First Gemma run (Taras's terminal, `results/guard_gemma.json`): mlx-lm runs Gemma 4 on the GPU.
  Load 5.8 s, about 2.0 s per request at 30 tokens. Score 5/10 is fake: every answer starts with
  `<|channel>thought` (the model thinks first), the 30 tokens run out inside the thinking, so the
  parser saw no YES and called all 10 "clean". `enable_thinking=False` does not change the prompt
  (checked: same string as the default). Fix to try in S5: prefill an empty thought block, or raise
  max_tokens and parse the text after the thinking ends. Not tested yet.

## 2026-11-24 · Docs trimmed
- PLAN cut from 800 to ~450 words; BRIEF from 450 to ~190 and refocused on what matters to Taras
  (PLAN = what we do, BRIEF = why). Call moved to 13:00; stop 12:30; mock only 15 minutes,
  because Taras learns by building, not by rehearsing. Steps run in priority order until time ends.

## 2026-11-24 · S0.5 smoke test
- `scripts/smoke.py` through the `SSL_CERT_FILE` fix: `models.list` shows `claude-haiku-5-5` and
  `claude-sonnet-5-5`; one Haiku call (max_tokens=5) replied "Hi there!" with 12 input and 5 output
  tokens. Usage also carries `cache_creation_input_tokens`, `cache_read_input_tokens` and a split
  of cache writes into 5-minute and 1-hour TTL: the S1 cost formula must read them.
- Decided before S1: normalisation trims whitespace but does not lowercase. Taras's reason: case
  can change meaning ("Apple" vs "apple") or be part of an ID (policy number `Ab12` vs `AB12`),
  and a wrong hit costs more than a missed one. Also new rule in CLAUDE.md: a short primer before
  every guess question, after Taras could not parse "hit rate of the exact cache" cold.

## 2026-11-24 · S1 exact cache (thin slice)
- `gateway/proxy.py`: POST /v1/messages; exact-cache key = sha256 of model, system, max_tokens,
  tenant, whitespace-normalised messages; cost log in SQLite `results/gateway.db`; 402 past the cap.
- Changed from plan: `temperature` left out of the key. SDK 2.13 has no `temperature` parameter
  (API version 2026-10-21 rejects it), and a field the provider ignores cannot change the answer.
  `max_tokens` is in instead: it can cut the answer short.
- Prices (USD/MTok, claude-api skill, cached 2026-11-03; S3 checks the live page): Haiku 5.5
  0.10 in / 0.50 out / 0.01 cache read; Sonnet 5.5 2 / 10 / 0.10; cache writes 1.25x (5 min), 2x (1 h).
- `scripts/s1_exact.py` on 30 made-up queries: hit rate 9/30 = 30% (6 repeats, 3 of 4 whitespace
  variants; 0 paraphrases, 0 case changes, 0 other-tenant). Taras guessed 10/30. The 4th whitespace
  variant ("e-bike ?") adds a space where there was none, which collapsing runs does not undo.
- Latency median: hit 0.64 ms, miss 577 ms (Haiku, ~60 output tokens). Taras guessed 1-10 ms / 0.5-1.5 s.
- Cost: 21 misses = $0.000656 total; hits saved ~$0.00028. 402 fires with the cap at $0.000001;
  a cached query is still served (hits are free, so the cap check sits after the cache lookup).
- Every answer is "I don't have the details": there is no policy document yet. S3 adds one to the
  system prompt, which is also what makes provider prompt caching worth having.
- Guess review: wrong hits in an exact cache come from an input that changes the answer but is not
  in the key (date, updated document, sampling). Cap overshoot is at most one request's worst cost,
  times N with N requests in flight; the fix is to reserve the worst case before the call.

## 2026-11-24 · S3 provider prompt caching (thin slice)
- Research verdict: Haiku 5.5 $0.10 in / $0.50 out / $0.125 5-min write / $0.20 1-h write /
  $0.01 read; Sonnet 5.5 $2 / $10 / $2.50 / $4 / $0.10. Minimum cacheable prefix 512 tokens for
  both; default TTL 5 minutes. Source: platform.claude.com/docs/en/about-claude/pricing and
  /build-with-claude/prompt-caching, read 2026-11-24 (no "last updated" date on either page).
  Matches the `PRICES` table in `gateway/proxy.py`.
- Breakpoint goes on the system block, not top-level: a top-level marker lands on the last message,
  so each new question would be inside the cached prefix and miss.
- `scripts/s3_prompt_cache.py`, made-up policy `data/policy.md` (1571 tokens) in system:
  A writes 1571, B and C read 1571 with only 18-19 fresh input tokens. Input cost B $0.0000175 vs
  D (no cache) $0.0001594: 9.1x cheaper per call, not 10x, because the question is full price.
  Whole call (with output) only 4x cheaper: output is now the bigger cost.
- Break-even: A+B $0.000216 vs D+D $0.000319, so caching already pays on the second call.
- Latency: no visible change at 1.5k tokens (585-638 ms all). The time win needs long prefixes.
- Short system (50 tokens): write 0, read 0, no error. Silent.
- Taras's guesses: 9x right in size, but he subtracted the one-time write from every call; it is
  paid once per 5 minutes. He thought caching is per conversation; it is stateless prefix matching
  across any requests. Timestamp at the start of system -> hit rate 0: right.
- Side note for S2: with no document (call F) Haiku invented a display reset (10 s, power button);
  the policy says power + minus for 5 s. Exact or semantic cache would store and repeat that answer.
