# cache-me-if-you-can: brief

Why this project exists and what matters to Taras. Read it to judge the work (critic, mock).
`PLAN.md` says what we do; it wins where they differ.

## Why
Taras has a technical call with TheTop's FDE engineer on 2026-11-24 at 13:00. TheTop's product,
TheEngine, is a gateway between a company and its AI providers: routing, caching, policy checks,
spend dashboard. His gaps: caching layers (never built one), routing, SQL basics, local AI.
He wants to say "I measured this", not "I would do it like this".

## What matters
- Understanding over typing. He learns by digging into a mechanism, not by memorising answers:
  the mock interview is minor, the building and measuring is the point.
- Each mechanism explained plainly, with where it stops working.
- Real numbers he measured himself: hit rate, wrong hits, $ saved, ms added.
- Spend stays tiny ($3) and nothing leaks: his key never printed, the shell's `OPENAI_API_KEY`
  never used (owner unknown), only made-up data in prompts.

## Related
- Call prep and TheEngine facts:
  `ai-job-search/documents/applications/thetop_applied_ai_engineer_fde/interview_prep_fde_call.md`.
- `~/Documents/Projects/dont-paste-that` reuses this proxy and the Gemma cache later.
