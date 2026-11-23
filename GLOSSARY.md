# Glossary

**cache-me-if-you-can**: a tiny AI gateway built to measure how caching, routing and local guards work.

- **gateway / proxy**: a service between an app and the AI providers. The app sends its request to the
  proxy; the proxy decides what to do (answer from cache, pick a model, block) and logs it.
- **exact cache**: stores answers under a hash of the normalised request. Hits only on the same request.
- **normalised request**: the request with differences that do not change the answer removed
  (key order, extra spaces, case where safe), so equal requests give equal hashes.
- **semantic cache**: stores answers under an embedding of the prompt. Hits when a new prompt is
  close enough in meaning (cosine similarity above a threshold).
- **embedding**: a list of numbers that places a text in space so texts with similar meaning are close.
- **similarity threshold**: the cut-off above which the semantic cache counts a hit. Too low gives
  wrong hits, too high gives no hits.
- **wrong hit**: a semantic cache hit that returns the answer to a different question
  (example: "policy 2024" answered with the "policy 2025" answer).
- **provider prompt caching**: the provider (Anthropic) stores the processed start of a prompt and
  charges less to reuse it. Shown as `cache_read_input_tokens` in the response.
- **hit rate**: hits divided by all requests.
- **cost log**: the SQLite table with one row per request: model, tokens, cost, cache hit, latency.
- **spend cap**: the proxy refuses with HTTP 402 when logged cost passes $2.50.
- **router**: picks the model per request: simple tasks to Haiku, hard ones to Sonnet.
- **guard**: a check that runs before a request leaves for the cloud. Here: regex and a local
  Gemma model looking for personal data.
- **critic**: a subagent in a fresh context that reviews the plan as a strict senior engineer.
