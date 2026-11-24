# Glossary

**cache-me-if-you-can**: a tiny AI gateway built to measure how caching, routing and local guards work.

- **gateway / proxy**: a service between an app and the AI providers. The app sends its request to the
  proxy; the proxy decides what to do (answer from cache, pick a model, block) and logs it.
- **tenant**: the customer a request belongs to (`x-tenant` header). Tenants never share a cache hit.
- **layer**: one stage of the proxy pipeline (guard, exact, semantic, router, claude). The cost log
  records which layer answered.
- **exact cache**: stores answers under a hash of the normalised request. Hits only on the same request.
- **normalised request**: the request with whitespace runs collapsed and trimmed, so requests that
  differ only in spacing give equal hashes. Case is kept: it can carry meaning (AB12 vs Ab12).
- **semantic cache**: stores answers under an embedding of the prompt. Hits when a new prompt is
  close enough in meaning (cosine similarity above a threshold).
- **embedding**: a list of numbers that places a text in space so texts with similar meaning are close.
- **similarity threshold**: the cut-off above which the semantic cache counts a hit. Too low gives
  wrong hits, too high gives no hits.
- **ID guard**: a semantic-cache check: every token with a digit (AB12, 2025) must match exactly.
- **wrong hit**: a cache hit that returns the answer to a different question. Semantic example:
  "policy 2024" answered with the "policy 2025" answer. Exact caches get them too, when something
  that changes the answer (document version, date) is not in the key.
- **provider prompt caching**: the provider (Anthropic) stores the processed start of a prompt and
  charges less to reuse it. Shown as `cache_read_input_tokens` in the response.
- **breakpoint**: the `cache_control` marker that ends the prefix the provider caches. Everything
  before it must be byte-identical across calls.
- **hit rate**: hits divided by all requests.
- **cost log**: the SQLite table with one row per request: model, tokens, cost, cache hit, latency, layer.
- **spend cap**: the proxy refuses with HTTP 402 when logged cost passes $2.50.
- **router**: picks the model per request: simple tasks to Haiku, hard ones to Sonnet.
- **guard**: a check that runs before a request leaves for the cloud. Here: regex and a local
  Gemma model looking for personal data.
- **fail closed**: when a check cannot decide (Gemma ran out of tokens), treat it as a block, not a pass.
- **critic**: a subagent in a fresh context that reviews the plan as a strict senior engineer.
