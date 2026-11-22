# ULTRON — private memory knowledge graph

## Reference and scope

The idea of a spatial, navigable map of connected notes was inspired by
[Second Brain Black Hole](https://github.com/williamwasen/second-brain-black-hole)
by williamwasen (MIT licensed). ULTRON does not vendor its source, shaders,
HTML, assets, or importer. This implementation uses ULTRON's own memory
records, provenance links, authentication, and deterministic layout data.

The reference project is deliberately a visualization plus Markdown importer;
it does not provide AI, memory storage, or synchronization. ULTRON keeps those
responsibilities in its own provider-independent core.

## API

`GET /v2/memory/graph?limit=300`

Required headers:
- `X-Installation-ID`
- `X-Installation-Token`

The route returns a read-only graph for the authenticated installation:
- `nodes`: memory ID, title, full text, kind, source, confidence, timestamps,
  access count, deterministic 3D position, and link degree.
- `edges`: index pairs pointing from a source memory to a derived memory.
- `edge_details`: stable memory IDs and the explicit relation name.
- `regions`: episodic, semantic, and procedural clusters.
- `truncated`: indicates that the requested node cap was reached.

The default cap is 300 and the hard cap is 500. Positions are stable for the
same installation and memory ID. The endpoint does not generate or infer
relationships from text: only explicit rows in `cognitive_memory_links`
become edges.

## Privacy and lifecycle

- The route requires installation authentication and filters every query by
  the authenticated installation ID.
- It never reads the legacy global conversation table.
- It does not update access counters, reindex vectors, write memories, or
  consolidate facts.
- The response contains the authenticated owner's note text. Treat it as
  private data; do not publish, cache publicly, or attach it to public issues.
- The route is an export contract for a future native/web visualizer, not a
  new source of truth. SQLite/PostgreSQL memory records remain authoritative.

## Validation

`tests/test_memory_knowledge_graph_api.py` covers explicit source edges,
read-only behavior, installation isolation, bounded output, and authentication.
The feature must remain behind the existing private installation headers.
