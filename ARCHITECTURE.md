# ULTRON core and replaceable model providers

## Ownership boundary

ULTRON owns its identity, system instructions, SQLite memory, tool registry, orchestration, execution limits, test runner, and publication policy. A model provider is an interchangeable reasoning/proposal adapter. Provider output is untrusted input and cannot alter core policy or authorize publication.

## Provider configuration

Select one adapter with `ULTRON_PROVIDER`:

- `gemini`: `GEMINI_API_KEY`, optional `GEMINI_BASE_URL`, `GEMINI_MODEL`
- `openai`: `OPENAI_API_KEY`, optional `OPENAI_BASE_URL`, `ULTRON_MODEL`
- `openrouter`: `OPENROUTER_API_KEY`, optional `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`
- `custom`: `ULTRON_API_KEY`, `ULTRON_BASE_URL`, `ULTRON_MODEL` (OpenAI-compatible API)

Changing the provider changes only the client/model configuration. It does not migrate, delete, or recreate `~/.ultron/memory.db` or `~/.ultron/system_prompt.txt`.

## Evolution flow

1. The selected model proposes a patch and affected paths.
2. ULTRON checks workspace containment, patch validity, execution budget, and sensitive paths.
3. ULTRON runs the configured local test command with a hard timeout.
4. ULTRON's deterministic policy engine rejects failed tests and requires human review for sensitive paths.
5. A passing change is eligible for a reviewable pull request. Direct merge and production publication are never authorized by model output or by a green test alone.

The orchestrator defaults to `python -m unittest discover -s tests`, caps test execution at 180 seconds, and captures bounded output. Integrations that apply patches must use an isolated branch/worktree and record the patch, test output, and decision alongside the proposal.

## Resource boundary

The core uses the Python standard library plus the existing OpenAI-compatible SDK. It does not keep a second model resident in memory. Only the selected provider is instantiated, keeping the core independent from provider lifecycle and suitable for constrained deployments.
