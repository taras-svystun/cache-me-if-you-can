# cache-me-if-you-can

A tiny AI gateway (FastAPI proxy in front of Claude) that Taras builds and measures to understand
caching, routing and local guards before his TheTop FDE call on 2026-11-24 at 13:00.

- `GLOSSARY.md`: the project's words. Use them in code, docs and commits.
- `docs/PLAN.md`: the plan, the session order and what we agreed. Read it when starting a step.
- `docs/journal.md`: what each finished step did, what we measured, and why. Read it before
  researching anything, and at the start of each session.
- `docs/critic.md`: the critic prompt. Read it when calling the critic.
- `docs/BRIEF.md`: why the project exists and what matters to Taras. Read it to judge the work (critic, mock). `PLAN.md` wins where they differ.

## Learning lab rules

Taras is learning AI gateway mechanisms: caches, routing, local models, cost logging.
Claude writes the code; Taras owns the ideas and must be able to explain every piece.
Taras writes code only where one line gives 90% of the understanding (the exact-cache key,
the SQL query): he tries, Claude corrects, move on.

Each step follows one loop: primer, Taras guesses the result, Claude builds, we measure, checkpoint.
The primer comes before any guess question: in about 30 seconds of reading, what the mechanism
does, what each metric in the question means and what a good or bad value feels like (a tiny
example). A question Taras cannot parse without it is a wasted question.
Explain each new piece by its mechanism: the idea, how the code works step by step, why it
behaves as it does, and where it stops working.

A long session opens with its map: the blocks, the time for each, the total. After each block,
say how far along we are and what is left.

## Project rules

- Budget: $3 of Anthropic API tokens. The proxy refuses with HTTP 402 when the logged cost
  passes $2.50. Taras's key lives in `.env` (gitignored). Never read or print it.
  Never use the `OPENAI_API_KEY` in the shell: owner unknown, may be a client's.
- Demos run in-process with FastAPI TestClient: no open port.
- Python TLS in the sandbox: `SSL_CERT_FILE` must point at a CA bundle, else HTTPS from Python
  fails with `OSStatus -26276`. `gateway/__init__.py` sets it to `certifi.where()`.
  Hugging Face downloads also need `HF_HUB_DISABLE_XET=1`.
- `HF_HOME=./.cache` (gitignored).
- Test data is made up. No real personal or company data in prompts.

## Finishing a step

- `README.md` has a copy-paste command for every way to run the project.
- The sandbox blocks writing to `.git`: Claude gives Taras one ready commit command, Taras runs it.
