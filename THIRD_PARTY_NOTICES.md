# Neural model provenance and scope

ULTRON's current `backend/fly_brain.py` is a small, independently written
leaky-integrate-and-fire (LIF) microcircuit. It does not copy source files or
connectome data from the upstream project and does not contain the FlyWire
whole-brain graph.

Scientific/software reference:
- https://github.com/eonsystemspbc/fly-brain
- The upstream project describes a FlyWire-based LIF simulation with roughly
  138,000 neurons and millions of synapses, plus Brian2, PyTorch, NEST GPU and
  GeNN runners.
- Upstream repository license: GPL-2.0. Its `code/paper-phil-drosophila`
  subdirectory contains a separately licensed MIT component; check the exact
  file-level license before copying any upstream source.

Important implementation boundary:
- ULTRON currently uses a compact local LIF circuit as its mandatory control
  signal for cognitive-cycle attention and specialist ordering.
- `is_full_connectome` is deliberately false.
- The upstream full-connectome simulator is not yet vendored, downloaded,
  loaded, or executed by ULTRON. It requires a large connectivity dataset,
  PyTorch/other scientific dependencies, and substantially more memory/CPU
  than the current lightweight Render deployment is known to provide.
- Do not describe this reduced circuit as the original fly brain or as a
  biologically complete/validated artificial intelligence.


## On-device language runtime and model

- ULTRON's optional iOS language-generation runtime uses
  [swift-llama-cpp](https://github.com/pgorzelany/swift-llama-cpp), pinned in
  the iOS workflow to commit
  `c0de205096bc735093a1b73107ca4fe52bf99877`. The wrapper is MIT licensed.
- The runtime downloads the official llama.cpp b11960 Apple XCFramework;
  its SHA-256 is verified by Swift Package Manager. The workflow separately
  builds the iOS Simulator slice from the matching upstream source revision.
  llama.cpp is MIT licensed.
- The optional model is Qwen3-0.6B Q4_K_M in GGUF format from
  `tauqir02/Qwen3-0.6B-GGUF`, derived from Qwen/Qwen3-0.6B. Its published
  file SHA-256 is verified before the app accepts the download:
  `373db06783953f0981572d008f183eb2167b93304f5adbf7c4ce6ed6a91ee437`.
  The Qwen3 model is Apache-2.0 licensed; retain the upstream model card and
  license when redistributing model weights. Model weights are downloaded by
  the user after installation and are not embedded in the IPA.
- The model is a small language-generation component, not the FlyBrain.
  The server-side FlyBrain runs first and sends non-private control signals;
  the local model uses those signals to phrase the response. It does not
  train or modify FlyBrain synapses or its connectome.
