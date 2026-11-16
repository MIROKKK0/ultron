#!/usr/bin/env python3
"""Run short, real-connectome smoke simulations and emit machine-readable evidence."""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.flywire_runtime import DATA_FILES, simulate, status

EXPECTED_REVISION = os.getenv(
    "ULTRON_FLYWIRE_REVISION",
    "a3db62f9436074e485c0278290c2164ed6150808",
)


def collect_provenance(root: Path) -> dict:
    """Record the exact upstream commit and immutable hashes of both datasets."""
    try:
        revision = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("Unable to identify the checked-out FlyBrain revision.") from exc

    files = []
    for relative_path in DATA_FILES:
        path = root / relative_path
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        files.append({
            "path": relative_path.as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": digest.hexdigest(),
        })
    return {"upstream_commit": revision, "data_files": files}


def main() -> int:
    current = status()
    if not current["available"]:
        raise SystemExit("FlyWire data/code unavailable: " + json.dumps(current, ensure_ascii=False))
    os.environ["ULTRON_FLYWIRE_ROOT"] = current["root"]
    provenance = collect_provenance(Path(current["root"]))
    if provenance["upstream_commit"] != EXPECTED_REVISION:
        raise SystemExit(
            f"Unexpected FlyBrain revision: {provenance['upstream_commit']} "
            f"(expected {EXPECTED_REVISION})"
        )
    results = [simulate("sugar", 0.01), simulate("p9", 0.01)]
    evidence = {
        "status": "passed",
        "provenance": provenance,
        "connectome": current,
        "simulations": results,
    }
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
