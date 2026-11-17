---
name: ultron-safe-iphone-actions
description: Plan and implement user-authorized native iPhone actions for ULTRON using supported iOS APIs.
---

# ULTRON Safe iPhone Actions

1. Identify the exact device capability and whether Apple exposes a supported public API.
2. Prefer App Intents / Shortcuts for user-invoked actions.
3. Request only the minimum permission and explain why before triggering the system prompt.
4. Require explicit confirmation before sending messages, creating or deleting data, purchases, account changes, or sharing private information.
5. Never promise unrestricted control of iOS or automate other apps through Accessibility hacks.
6. Keep secrets out of the IPA; use per-installation identity and server-side authorization.
7. Add tests for permission denial, cancellation, malformed input, and successful operation.
8. Build the simulator and device targets in GitHub Actions. Report physical-device testing separately.
9. Deliver changes through a branch and pull request; do not self-merge or deploy.
