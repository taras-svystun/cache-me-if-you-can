# cache-me-if-you-can

A tiny AI gateway: a FastAPI proxy in front of Claude with an exact cache, a semantic cache,
provider prompt caching, a model router, a local personal-data guard and a SQLite cost log.
Built to measure how each mechanism behaves.

## Setup
```
python3 -m venv .venv
cd ~/Documents/Projects/cache-me-if-you-can && read -s "k?Key: " && printf 'ANTHROPIC_API_KEY=%s\n' "$k" > .env && unset k
```

## Run
Commands are added as each step lands.

### S0.5 Smoke test (one tiny Haiku call)
```
cd ~/Documents/Projects/cache-me-if-you-can && SSL_CERT_FILE=.venv/lib/python3.11/site-packages/pip/_vendor/certifi/cacert.pem .venv/bin/python scripts/smoke.py
```

### S1 Exact cache, cost log, 402 (about 30 Haiku calls, under $0.001)
```
cd ~/Documents/Projects/cache-me-if-you-can && SSL_CERT_FILE=.venv/lib/python3.11/site-packages/pip/_vendor/certifi/cacert.pem .venv/bin/python scripts/s1_exact.py
```

### S3 Provider prompt caching (6 Haiku calls, under $0.001)
```
cd ~/Documents/Projects/cache-me-if-you-can && SSL_CERT_FILE=.venv/lib/python3.11/site-packages/pip/_vendor/certifi/cacert.pem .venv/bin/python scripts/s3_prompt_cache.py
```

### S2 Semantic cache thresholds (no API calls, CPU)
```
cd ~/Documents/Projects/cache-me-if-you-can && HF_HOME=./.cache HF_HUB_OFFLINE=1 .venv/bin/python scripts/s2_semantic.py
```

### S4 Router (20 answer calls + 10 router calls, about $0.02)
```
cd ~/Documents/Projects/cache-me-if-you-can && SSL_CERT_FILE=.venv/lib/python3.11/site-packages/pip/_vendor/certifi/cacert.pem .venv/bin/python scripts/s4_router.py
```

### S5 Gemma guard (run in your own terminal, not in Claude Code: it needs the GPU)
```
cd ~/Documents/Projects/cache-me-if-you-can && HF_HOME=./.cache HF_HUB_OFFLINE=1 .venv/bin/python scripts/gemma_guard.py
```
Prints the device, load time, then streams Gemma's verdict on 10 made-up requests, with OK/MISS and
seconds each. Saves `results/guard_gemma.json`.
