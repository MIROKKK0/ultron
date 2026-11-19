# ULTRON — neural memory explorer

## Product contract

The explorer is a private, read-only lens over ULTRON's canonical memory store.
It must not become a second memory database and must not silently rewrite facts.

### 3D interaction

- Render memory records as selectable nodes in a 3D scene.
- Use the server-provided stable positions as an initial layout, then allow local
  camera rotation, zoom, pan, and focus without writing coordinates back.
- Draw edges only from explicit provenance relations. Similarity candidates
  must use a visually distinct, non-authoritative style.
- Selecting a node opens its content, type, source, confidence, timestamps,
  access count, and provenance chain.
- Provide keyboard/accessibility alternatives: searchable list, filters, and
  a textual detail panel. The iOS client must remain usable without 3D.

### Knowledge diagnostics

The private insights endpoint reports:
- repeated-content candidates using transparent lexical Jaccard similarity;
- missing memory kinds in the analyzed set;
- records with no explicit provenance edges;
- low-confidence records.

These are review signals, not semantic truth. No automatic merge, deletion,
confidence increase, or memory creation is permitted. A future semantic
duplicate model must be benchmarked against a frozen, owner-approved dataset
and show per-case evidence before it can make recommendations.

### Six-specialist workflow

1. Planner defines the investigation and bounded scope.
2. Memory retriever fetches relevant owner-scoped records.
3. Solver drafts a candidate relationship or knowledge summary.
4. Critic checks source coverage, contradiction risk, and unsupported claims.
5. Memory curator proposes (never commits) a consolidation with source IDs.
6. Evaluator scores coverage, evidence traceability, and regression/safety checks.

Every specialist result must include role, input scope, evidence IDs, status,
and whether it performed a write. For this explorer all specialist operations
are advisory; writes remain behind the existing explicit curation approval.

### Privacy and performance

- All graph and diagnostics routes require installation credentials.
- Every query is scoped to the authenticated installation.
- Bound graph size and pairwise duplicate analysis; never expose memory text
  in public telemetry, logs, screenshots, or issue comments.
- Do not send memory content to Gemini or another provider by default.
- Cache only in private client memory and clear it on logout/revocation.

## Current implementation boundary

The graph API is implemented in PR #65. This milestone adds bounded,
read-only diagnostics and tests. A full WebGL2/SceneKit renderer and live
specialist execution panel remain separate follow-up work; this document does
not claim they are already shipped.
