# ULTRON conversational language layer

ULTRON keeps FlyBrain as its required neural/control subsystem. FlyBrain is not
a text-generating language model, so open-ended conversation needs a separate
language model. The app supports two paths:

1. **On-device:** Qwen through llama.cpp/Metal on the iPhone. It can work offline
   after the model has been downloaded, but quality and speed are limited by the
   phone and the selected model.
2. **Optional online provider:** any HTTPS provider exposing the OpenAI-compatible
   `/chat/completions` API. The API key is stored only in the backend environment,
   never in the iOS app or repository.

## Backend environment

Configure these server-side environment variables (for example, in the Render
service environment settings):

- `ULTRON_LLM_BASE_URL`: provider API base URL, ending before
  `/chat/completions`.
- `ULTRON_LLM_API_KEY`: private provider API key.
- `ULTRON_LLM_MODEL`: exact model identifier offered by the provider.
- `ULTRON_LLM_NAME` (optional): short display name for diagnostics.

If the three required values are absent, ULTRON stays on the local FlyBrain/Qwen
path. If the online provider fails, the backend falls back to the existing
local response path; it does not fabricate an online answer.

## Safety and privacy

- Never put provider keys in Swift source, app settings, GitHub commits, or logs.
- Public chat does not read shared private memories or conversations.
- Only a bounded recent conversation history is sent to the configured provider.
- Tool execution, memory writes, and other side effects remain separate from
  natural-language generation and must have explicit authorization.
- A provider being configured does not mean it is free or permanently available.
  Free-tier quotas and model names are controlled by the provider.

## Remaining product work

Streaming from the online provider, per-installation private memory, voice I/O,
tool-call approval UX, cancellation, and device-side latency benchmarking are
separate milestones. This adapter intentionally does not claim those are done.
