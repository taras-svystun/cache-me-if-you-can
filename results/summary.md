# Results, 2026-11-24 (made-up data, small sets: directions, not benchmarks)

| Mechanism | Hit / catch rate | Wrong rate | $ saved | ms added |
|---|---|---|---|---|
| Exact cache (S1) | 9/30 = 30% | 0 | 100% per hit (~$0.00003 per Haiku call) | +0.6 ms on a hit; a miss takes 577 ms |
| Provider prompt cache (S3) | 1571/1590 input tokens read from cache | 0 (same answer quality) | input 9.1x cheaper per call; whole call 4x; pays off from call 2 | ~0 at 1.5k tokens |
| Semantic cache 0.90 + ID guard (S2) | 4/5 paraphrases | 1 wrong in 8 traps (before/after ships, sim 0.995) | like the exact cache, per hit | +8 ms (embedding on CPU) |
| Router, rules or Haiku (S4) | 10/10 routes right | 0 misroutes | 46% vs all-Sonnet (Haiku alone also solved the hard tasks: ~95%) | rules 0; Haiku router +500 ms |
| Regex guard (S5) | 10/10 seen rows, 0/4 unseen | 1 false alarm in 6 clean rows | n/a | ~0.01 ms |
| Gemma guard (S5) | 10/10 where it finished; 4/14 ran out of tokens while thinking | 0 false alarms in 6 clean rows; the run was fail-open on the 4 unfinished; parser now fails closed (re-scored 14/14, 4 by luck) | n/a | +17.7 s per request (GPU, thinking) |
| Spend cap with reservation | 10 parallel, room for 3: old check passed 10 (286% of cap), reservation 3 (86%) | reserve 5.3x the real Haiku cost, so the cap blocks early; late only if a text beats the 2-chars-per-token estimate | n/a | 1 SQLite write per miss |
| Full pipeline vs naive (all Sonnet, no caches) | 14/32 never called a model; 2 PII blocked | 0 wrong semantic hits (no traps in this set) | 99% | median 490 ms vs 694 ms |

Total API spend for all of it: $0.19 of the $3 budget.

## Six lines for the call
1. Start cheap and measure: Haiku 5.5 solved our "hard" tasks, so the router's value was smaller
   than the plan assumed.
2. A wrong hit comes from something that changes the answer but is missing from the key
   (tenant, document version, date). In an exact cache it leaks; in a semantic cache it hides.
3. Embeddings ignore small words that flip meaning (before/after: 0.995). No threshold fixes
   that; structured guards (IDs exact) fix part of it.
4. Provider caching needs a byte-identical prefix of 512+ tokens: put stable content first,
   volatile content (time, IDs) after the breakpoint.
5. A guard must fail closed: Gemma's unfinished checks were first counted as clean.
6. Spend caps overshoot by one request (N with concurrency); reserve the worst case before the call
   (measured: 10 parallel calls hit 286% of the cap without it, 86% with it).
