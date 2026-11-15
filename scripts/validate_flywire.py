#!/usr/bin/env python3
"""Run real FlyWire smoke simulations and record reproducible resource evidence."""
from __future__ import annotations

import json
import os
import resource
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.flywire_runtime import simulate, status


def peak_rss_mib() -> float:
    # Linux reports KiB; macOS reports bytes.
    value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return round(value / (1024 if sys.platform != "darwin" else 1024 * 1024), 2)


def main() -> int:
    current = status()
    if not current["available"]:
        raise SystemExit("FlyWire data/code unavailable: " + json.dumps(current, ensure_ascii=False))
    os.environ["ULTRON_FLYWIRE_ROOT"] = current["root"]

    started = time.perf_counter()
    results = [simulate("sugar", 0.01), simulate("p9", 0.01)]
    elapsed = round(time.perf_counter() - started, 3)
    if any(item["neurons"] < 130_000 or item["steps"] != 100 for item in results):
        raise SystemExit("Unexpected connectome size or simulation step count.")

    evidence = {
        "status": "passed",
        "connectome": {
            "name": current["connectome"],
            "expected_neurons": current["expected_neurons"],
            "backend": current["backend"],
        },
        "simulations": results,
        "benchmark": {
            "wall_time_seconds_for_both_experiments": elapsed,
            "peak_process_rss_mib": peak_rss_mib(),
            "cpu_threads": int(os.getenv("ULTRON_FLYWIRE_THREADS", "2")),
            "note": "CI runner measurement only; not a Render or iPhone performance guarantee.",
        },
    }
    rendered = json.dumps(evidence, ensure_ascii=False, indent=2)
    print(rendered)
    output = Path(os.getenv("FLYWIRE_VALIDATION_OUTPUT", "artifacts/flywire-validation.json"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered + "\\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
