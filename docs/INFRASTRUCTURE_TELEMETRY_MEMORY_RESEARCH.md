# ULTRON infrastructure: telemetry, research and contextual memory

## Deployment shape
- Render remains the lightweight FastAPI service; no model training or vector database runs inside the 512 MB web process.
- PostgreSQL stores metadata, installation credentials, memories and aggregate telemetry.
- GitHub Actions trains/evaluates experimental Transformer checkpoints.
- Gemini remains the production generator and provides optional semantic embeddings for memory.
- No new paid observability or vector database service is required for this first implementation.

## Privacy-safe telemetry
The middleware stores request route template, method, HTTP status and latency. Model calls store provider/model name, latency, provider-reported input/output token counts and cost only when both token prices are explicitly configured. Tool decisions, citation audit scores and explicit user-feedback scores are stored as metadata.

The telemetry table never stores prompt text, completion text, retrieved snippets, user comments, IP addresses, installation IDs, bearer tokens, API keys or request bodies. Errors are recorded by exception class only. The authenticated GET /telemetry/summary endpoint returns a seven-day aggregate with request count, failure rate, p50/p95 latency, token totals, estimated cost and quality sample count.

Optional pricing configuration:
- ULTRON_INPUT_USD_PER_MILLION
- ULTRON_OUTPUT_USD_PER_MILLION

If provider token usage or pricing is unavailable, the corresponding metric remains null/unknown; the backend must not invent it.

## Installation identity and private memory
The iOS client creates a random installation UUID and a separate random installation token. Both are stored in iOS Keychain with AfterFirstUnlockThisDeviceOnly; the server stores only the SHA-256 hash of the token. Registration is idempotent for the same credential. Memory routes require both headers and verify the token before every operation.

Routes:
- POST /installations/register
- POST /memory
- GET /memory
- GET /memory/search?q=...
- DELETE /memory/{id}

New memories expire after 30 days. Reads, searches, deletes and chat context retrieval always filter by the authenticated installation ID. A cross-installation delete returns 404. The old legacy rows without an installation ID are not exposed to any installation and are not automatically migrated into a user's memory.

Memory embeddings use the existing Gemini API key and gemini-embedding-2 at 768 dimensions. Vectors are stored as JSON in PostgreSQL and cosine-ranked within the authenticated tenant; this is appropriate for the current small bounded store, not a replacement for a large vector database. If embeddings are not configured or fail, lexical retrieval remains available and the response reports that semantic embeddings were not used. Memory text is sent to Google's embedding endpoint when embedding is enabled; users should only store content they are comfortable processing through their configured Gemini account.

The installation token is a bearer credential. Never log it, include it in analytics, or commit it. Reinstalling the app creates a new installation namespace; old memories remain inaccessible unless an explicit account-level recovery feature is designed.

## Research quality
The DDGS search layer now:
- canonicalizes HTTPS URLs and strips common tracking parameters;
- rejects localhost, non-global IP literals and HTTP results;
- deduplicates canonical URLs;
- reranks candidates with BM25 plus title/snippet overlap and a small domain prior;
- preserves search-engine publication dates as unverified hints;
- labels URL validation separately from content verification.

The Gemini synthesis prompt treats retrieved titles/snippets as untrusted data and explicitly rejects embedded instructions. Citation audit compares URLs in the generated synthesis against the retrieved URL allowlist. Original source URLs are appended by the backend.

Important limitation: the current backend validates URL structure and citation membership, but does not fetch every page to independently verify its content, publisher identity or publication date. A source marked URL-valid is not necessarily fact-checked.

## Task-specific Transformer
training/generative/ultron_specialist_v1.jsonl is an original, curated dataset for narrow ULTRON behaviors: source handling, citation discipline, prompt-injection resistance, privacy-safe telemetry, tenant memory, and evaluation policy. The eval split is held out from SFT.

GitHub Actions trains a separate checkpoint and runs scripts/evaluate_ultron_specialist.py. The evaluator reports exact lexical criterion coverage on held-out cases. This is a reproducible task rubric, not a human-quality judge or proof of factuality. Keep the model experimental; Gemini remains the production generator.

## Operational checks
After merge/deploy:
1. Register an iOS installation and verify /memory returns only that installation's records.
2. Verify a second installation cannot read or delete the first installation's memory.
3. Verify expiry cleanup and explicit deletion.
4. Inspect /telemetry/summary and ensure it contains aggregates only.
5. Verify Gemini token counts appear only when returned by the provider; configure pricing separately if cost estimates are desired.
6. Verify research ranking, source URL canonicalization, prompt-injection tests and citation audit.
7. Compare specialist checkpoint reports over the same held-out benchmark before considering promotion.

## Sources
- OpenTelemetry GenAI metrics and agent/tool-call conventions: https://github.com/open-telemetry/semantic-conventions-genai
- Google Gemini Embeddings API: https://ai.google.dev/gemini-api/docs/embeddings
- Qdrant multi-tenancy design and tenant filtering: https://qdrant.tech/documentation/manage-data/multitenancy/
- OWASP LLM Top 10, including prompt injection and sensitive information disclosure: https://owasp.org/projects/top-10-for-large-language-model-applications
