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
