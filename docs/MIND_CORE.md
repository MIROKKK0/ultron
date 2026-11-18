# ULTRON Mind Core

ULTRON's memory is a local-first, append-only record. Original entries are never rewritten by agent output. Summaries, tags, links and other interpretations live in separate tables with explicit agent provenance.

## Guarantees

- **Source preservation:** original text is immutable through the public API; corrections append a new entry with `supersedes_id`.
- **Provenance:** each entry records its speaker, source, UTC timestamp and SHA-256 content fingerprint.
- **Separate derivations:** agent summaries and interpretations cannot overwrite original text.
- **Append-only audit chain:** every write adds a hash-linked event to `mind_ledger`; `verify_integrity()` checks the chain and source fingerprints.
- **Local custody:** SQLite is stored at the caller-provided path; this module makes no network requests and sends no records to model providers.
- **Portable foundation:** standard-library Python and SQLite only.

## API

```python
from ultron_mind import MindCorpus

mind = MindCorpus("~/.ultron/memory.db")
entry_id = mind.record("I chose a local-first architecture.", speaker="user", kind="decision")
mind.derive(entry_id, "Keep source text separate from agent notes.", agent="ultron")
mind.tag(entry_id, "architecture", agent="ultron")
print(mind.context_for("local-first"))
print(mind.verify_integrity())
```

Expand the core through tested adapters for imports, semantic indexing, encrypted backups, consent-scoped model access and agent tools. Keep each adapter replaceable; the record remains the durable source of truth.

## Verification

```bash
python -m unittest discover -s tests -v
```

This implementation is an independent design based on general local-first memory and provenance principles. It does not copy MindCorpus source code, interface, assets or proprietary design.
