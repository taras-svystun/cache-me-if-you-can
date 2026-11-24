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

## 2026-11-24 · S2 semantic cache (thin slice)
- `gateway/semantic.py`: MiniLM (all-MiniLM-L6-v2, 384 numbers, CPU), nearest same-tenant entry by
  cosine; optional ID guard: tokens with a digit (AB12, 2025) must match exactly, case included.
  Not wired into the proxy yet; measured offline with `scripts/s2_semantic.py` (0 API calls).
- Cache: 12 originals + "2025 return policy". Tests: 5 paraphrases, 8 traps.
- Result (right hits of 5 / wrong hits): 0.95 off 2/4, on 2/1; 0.90 off 4/4, on 4/1;
  0.85 off 4/6, on 3 wrong; 0.80 and below: 4 right, 7-8 wrong off, 4-5 on.
  Best here: 0.90 with the guard, 4/5 right, 1 wrong.
- The wrong hit no threshold can block: "cancel before it ships" vs "after it ships", sim 0.995,
  higher than every true paraphrase (0.91-0.96). The embedder barely weighs before/after.
  "Policy 2024 vs 2025" sim 0.981 and AB12/AB13 0.962: the guard blocks both.
- One paraphrase ("How many days do I have to return...") lands nearest to the service question
  (0.72), not to the return one: a low threshold would answer with the wrong topic.
- Embedding adds 8 ms median per query on CPU. Taras guessed 100-500 ms.
- Taras's guesses: threshold depends on domain and on the cost of a wrong hit vs a recompute; he
  would go high: matches the data. Flat tyre vs cracked frame: he said <= 0.8, it was 0.64.
  Block AB12/AB13 by exact match on ID-like tokens: that is the guard used here.
- Code fix during the step: first version counted a hit as right when the label said "same answer"
  without checking WHICH entry was nearest; the 0.70 row showed a false right hit. Labels now name
  the expected cached question.

## 2026-11-24 · S4 router (thin slice)
- `gateway/router.py`: rules router (hard words or > 140 chars -> Sonnet) and Haiku classifier
  ("simple"/"hard", unsure -> hard). Both lean to Sonnet when unsure: Taras's call, a wrong answer
  costs more than overpaying.
- `scripts/s4_router.py`, 10 tasks (6 simple lookups, 4 hard: refund arithmetic, AB12 conditions,
  model choice, customer email), each run on both models; answers in `results/router_answers.md`.
- Both routers: 0 misroutes. Cost: all-Sonnet $0.0185, routed $0.0099 = 46% saved; the Haiku
  router's own calls cost $0.000144 (under 1% of all-Sonnet) but add ~500 ms per request, which
  roughly doubles the latency of a simple Haiku answer (~600 ms).
- Taras guessed ~2x saving (right: 46%), router ~5% of cost (actual < 1%), +500 ms (right).
- The surprise: Haiku 5.5 got the "hard" ones right too (refund 2,720 EUR on task 7; both failed
  AB12 conditions on task 8). Sonnet adds detail, not correctness, on this set. So all-Haiku would
  save ~95%. Lesson: measure quality per task class first; a router pays only where the cheap
  model actually fails. Quality judged by Claude on 2 tasks; Taras has not judged yet (stated limit).
- Sonnet task 1 cost $0.0047 vs ~$0.0008 for the next simple ones: it paid the cache write of the
  policy prefix. Caches are per model, so routing between two models writes two caches.

## 2026-11-24 · S5 local guard, regex side (thin slice)
- `gateway/guard.py`: regex for email, French phone, IBAN, dd/mm/yyyy date, street address.
  `scripts/s5_regex_guard.py` reads the rows from `scripts/gemma_guard.py`.
- 10/10 on the original 10 rows, about 10 microseconds each. Not a fair score: Claude wrote the
  patterns after seeing the rows. Its "health data" catch on row 7 came from the birth date, not
  the word "diabetes".
- 4 rows added after the regex was written: 0/4. Missed: health data with no date ("has HIV"),
  spelled-out email ("jean dot martin at gmail dot com"), +33 phone format. False alarm: an order
  number shaped like a phone and a shipping date. Total 10/14.
- Taras's guesses: names are hard for regex (right: no pattern finds "Marie Dupont"; row 2 was
  caught by the phone only). False alarm from @-like text (right in kind: shape without meaning).
- Gemma fix, not yet run: `MAX_TOKENS` 30 -> 400, and `verdict()` reads only the last line after
  the last channel marker, so YES/NO inside the thinking does not count. Checked offline on 4 made-up
  strings; the real run needs Taras's terminal (GPU).

## 2026-11-24 · S5 Gemma run (Taras's terminal)
- 10/14 correct, 17.7 s per row on average, load 5.0 s (`results/guard_gemma.json`).
- On the 10 rows where Gemma reached a verdict: 10/10, including the spelled-out email and +33
  phone that regex missed, and Macron as a public figure. The 4 misses all ran out of the
  400-token budget mid-thinking (~20 s each, 1.4-1.7k characters of thought), and the parser
  read "no verdict" as clean: fail-open, so 4 PII rows would have reached the cloud.
- Fix applied: `verdict()` fails closed (no final YES/NO counts as PII). On the saved answers
  that scores 14/14, but 4 of those are luck: the unfinished rows happened to be PII rows.
- Taras guessed 12-13/14 and 4-6 s. The time was 3x his guess: thinking tokens, ~20 tokens/s.
- Next for speed (not done): stop the thinking (prefill an empty thought block in the prompt),
  then re-run; a guard that costs 18 s per request is not usable in front of a 0.6 s Haiku call.

## 2026-11-24 · Pipeline: all layers in one proxy
- `gateway/proxy.py` now runs guard (regex) -> exact cache -> semantic cache (0.90 + ID guard,
  scoped by tenant, model, system, max_tokens) -> spend cap -> router (`model: "auto"`, rules)
  -> Claude, with per-layer times in `trace_ms` and a `layer` column in the cost log.
- Bug found on the first run: every request was blocked (422). Cause: the guard also scanned the
  system prompt, and the made-up policy holds a public service email (`scan(policy)` -> ['email']).
  Fix: scan user messages only; the system prompt is the operator's own text. The demo script also
  hid the cause by labelling any non-200 as "blocked"; now only 422 is.
- `scripts/s6_pipeline.py`, 30 S1 queries + 2 PII rows, vs naive (all Sonnet, no caches):
  layers: claude 16, exact 9, semantic 5, blocked 2. Cost $0.000825 vs $0.0834: 99% saved.
  Median latency 490 ms vs 694 ms. PII sent to cloud: 0 vs 2.
- Where the 99% comes from: the rules router sent every miss to Haiku (20x cheaper per token),
  provider caching made the policy input ~9x cheaper, and 14/32 requests never called a model.
- All 5 semantic hits were right on reading the answers (2 paraphrases, case, "e-bike ?" that the
  exact cache missed, after-shipping paraphrase). No trap queries in this set, so 0 wrong hits says
  little: the S2 traps are the real test.
- Median ms per layer: guard 0.35, exact 0.1, semantic 10.2, router 0.15, claude 578,
  store 15 (embedding the new question for the semantic cache, paid on every miss).
- Taras's guesses: guard first because it is local and before anything stores the prompt (right:
  caches and the log store it, Claude sends it out). Saving 50-70% (actual 99%; he did not count
  that the router and provider caching multiply). Semantic hits 10/30 (actual 5; exact took 9).

## 2026-11-24 · Tidy
- 15 cuts proposed; a read-only subagent checked each before any edit. Done: stale PLAN lines
  (temperature in the key, S5 open, Time holding steps, "S6 Streaming"), Rules that repeated
  CLAUDE.md, BRIEF key clause, GLOSSARY fixes + 5 terms, Gemma row history in `summary.md`,
  proxy docstring, `log()` inlined, `layer` in CREATE (the live DB already had it: 185 rows, $0.1884
  kept), guard/router imports at top, semantic `tenant` -> `scope`, guard rows in
  `data/guard_rows.json` (with `seen`), `reset(run_id)` shared by 4 demos, `requirements.txt`.
- Held back, the subagent found they break: `smoke.py` importing `gateway` (scripts/ is on
  sys.path, not the root); env defaults in `load_env()` (huggingface_hub reads `HF_HOME` and
  `HF_HUB_OFFLINE` at import, and s2/s6 load MiniLM before `load_env()` runs). README env prefixes
  stay until that moves to `gateway/__init__.py`.
- Checked offline: all files compile; regex 10/14; S2 threshold table unchanged; 422, 402 and an
  exact hit through TestClient on a temp DB. Not re-run: s1/s3/s4/s6 (API cost), Gemma (GPU).
- Follow-up, both held items done: env defaults live in `gateway/__init__.py` (runs before any
  `gateway.*` import, so before huggingface_hub reads them); `gemma_guard.py` sets HF_HOME/OFFLINE
  itself; `smoke.py` uses `client()` with the sys.path line. Cert bundle is now `certifi.where()`
  (newer than pip's copy). Checked with the three env vars unset: smoke lists both models and
  Haiku replies; s2 runs offline at 8.6 ms per embed. README commands have no env prefix now.
