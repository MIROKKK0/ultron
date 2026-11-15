#!/usr/bin/env python3
"""Run short, real-connectome smoke simulations and emit machine-readable evidence."""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.flywire_runtime import simulate, status

def main() -> int:
    current = status()
    if not current["available"]:
        raise SystemExit("FlyWire data/code unavailable: " + json.dumps(current, ensure_ascii=False))
    os.environ["ULTRON_FLYWIRE_ROOT"] = current["root"]
    results = [simulate("sugar", 0.01), simulate("p9", 0.01)]
    evidence = {"status": "passed", "connectome": current, "simulations": results}
    rendered = json.dumps(evidence, ensure_ascii=False, indent=2)
    print(rendered)
    output = Path(os.getenv("FLYWIRE_VALIDATION_OUTPUT", "artifacts/flywire-validation.json"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered + "\n", encoding="utf-8")
    if any(item["neurons"] < 130_000 or item["steps"] != 100 for item in results):
        raise SystemExit("Unexpected connectome size or simulation step count.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
