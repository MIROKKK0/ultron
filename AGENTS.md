# ULTRON repository rules

## Product invariants
- ULTRON's production language path must remain its own code and weights trained from random initialization.
- Do not add FlyBrain, FlyWire, hosted AI providers, third-party pretrained model weights, or hidden model fallbacks.
- Public chat must remain usable without secrets. Never embed server-wide credentials in the IPA.
- The 512 MB backend budget is a hard constraint; training must run in GitHub Actions, never inside the web service.
- Experimental generative checkpoints must not replace the deterministic production path until held-out evaluation, security review, and memory/latency gates pass.

## Change process
1. Reproduce bugs with a test before changing code.
2. Make one focused change in a branch.
3. Run unit tests, model smoke tests, iOS simulator/device builds when iOS files change, and live API checks when backend routes change.
4. Record corpus source, license, split hashes, tokenizer version, model config, validation/test metrics and artifact checksum for every training run.
5. Compare against the previous baseline; reject changes that improve train loss but regress validation/test or safety.
6. Never commit raw private user conversations, secrets, signing material, or unreviewed datasets.
7. Do not merge, deploy, publish an IPA, or replace a production model unless the release gates pass and the human owner has approved the action.

## iOS boundaries
- Use public iOS APIs, App Intents, Shortcuts and explicit user permission.
- Destructive, financial, communication, or privacy-sensitive actions require confirmation.
- No accessibility hacks, silent control of other apps, arbitrary shell execution, or background actions without OS permission.
