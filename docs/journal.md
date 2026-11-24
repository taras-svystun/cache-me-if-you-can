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
