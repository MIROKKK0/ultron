# ULTRON cognitive runtime — next implementation milestones

## Local semantic encoder

The contrastive trainer uses only ULTRON Tiny and the project-owned byte tokenizer:

```bash
python -m training.generative.train_semantic_encoder \
  --train-pairs training/semantic/train.pt-br.jsonl \
  --eval-pairs training/semantic/eval.pt-br.jsonl \
  --output artifacts/ultron-semantic-encoder.pt
```

The current dataset contains 32 training pairs and 61 frozen held-out PT-BR pairs, with exact-text leakage checks. Evaluation reports Recall@1/5/10, MRR, median rank, P90 rank and per-case ranks. Candidate acceptance requires higher MRR than the untrained baseline and zero per-case ranking regressions. This is a stronger diagnostic set, not proof of broad semantic understanding; add independently authored hard-negative suites and human review before enabling `ULTRON_MEMORY_ENCODER=neural` in production.

## Transformer during reasoning

The six-stage local cycle now records:
1. planner
2. solver
3. critic
4. memory retriever
5. memory curator
6. evaluator

The curator produces a proposal only. It never commits a semantic memory by itself. The evaluator runs the cycle gate and is included in the returned stage list. Research is an optional tool stage.

The Tiny Transformer can be selected explicitly with:

```bash
ULTRON_LOCAL_GENERATIVE_ENABLED=true
ULTRON_GENERATIVE_CHECKPOINT=/absolute/path/to/ultron-tiny.pt
```

This mode uses the retrieved memory and bounded conversation context in its prompt. It is experimental; the model is not instruction-tuned to general-assistant quality and is not enabled by default. A missing or invalid checkpoint is an explicit error, not a silent switch to an external provider.

## iPhone offline queue and history import

- `/remember texto` saves immediately when online. On transient network/server failures, it writes an AES-GCM encrypted queue in Application Support; the encryption key is derived from the installation token held in Keychain.
- `/sync` flushes queued entries. The app also attempts a flush on the next chat request. An entry is removed only after the server acknowledges it.
- `/import-history` explicitly sends up to 500 local chat messages to the authenticated `/v2/memory/import` endpoint. Roles and local timestamps are retained; server-side source hashes deduplicate repeated imports.
- The server still scopes every operation to the authenticated installation. No global legacy conversation table is read.

## Promotion policy

CI success validates code paths, not model quality. Checkpoint promotion remains blocked until the expanded frozen benchmark passes its MRR and zero-per-case-regression gate, independent hard-negative tests and human review. No merge, deployment or production checkpoint replacement is performed by these workflows.
