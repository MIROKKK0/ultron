# Development skills versus runtime skills

The files in `skills/` are instructions for repository-aware coding agents. They help an authorized developer or agent work safely on ULTRON's source code; they are not executable abilities inside the iOS app.

The production runtime skills are implemented in `backend/skills.py` and are constrained by the local decoder and public iOS APIs. Keeping these two kinds of skills separate prevents a documentation file from being mistaken for an installed runtime capability.

- `ultron-tdd-loop`: reproduce defects, add regression tests, verify the full stack.
- `ultron-safe-evolution`: observe metrics, propose one reversible change, train/evaluate from scratch, and require human review.

These replace earlier development proposals that depended on FlyBrain. ULTRON's current project rules explicitly prohibit FlyBrain, FlyWire, external hosted AI providers and third-party pretrained weights.
