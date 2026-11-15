#!/usr/bin/env python3
"""Run short, real-connectome smoke simulations and emit machine-readable evidence."""
from __future__ import annotations
import json
import os
from backend.flywire_runtime import simulate, status

def main() -> int:
    current = status()
    if not current["available"]:
        raise SystemExit("FlyWire data/code unavailable: " + json.dumps(current, ensure_ascii=False))
    os.environ["ULTRON_FLYWIRE_ROOT"] = current["root"]
    results = [simulate("sugar", 0.01), simulate("p9", 0.01)]
    print(json.dumps({"status": "passed", "connectome": current, "simulations": results},
                     ensure_ascii=False, indent=2))
    if any(item["neurons"] < 130_000 or item["steps"] != 100 for item in results):
        raise SystemExit("Unexpected connectome size or simulation step count.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
