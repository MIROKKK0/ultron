#!/usr/bin/env python3
import json, os
from pathlib import Path

kind = os.environ.get("TARGET_TYPE", "unknown")
reports = Path("reports")
reports.mkdir(exist_ok=True)
parts = [f"ULTRON isolated reverse-engineering worker: {kind}"]
if kind == "site":
    path = reports / "site-session.json"
    if path.exists():
        data = json.loads(path.read_text())
        parts += [
            f"Origin: {data.get('requestedOrigin')}",
            f"Final URL: {data.get('finalUrl')}",
            f"Title: {data.get('targetTitle')}",
            "REA evidence steps: " + ", ".join(data.get("steps", [])),
            "Browser profile: isolated, disposable, no user cookies",
        ]
    for name in ("web-inspection.json", "web-bundle-analysis.json", "web-session-observation.json"):
        p = reports / name
        if p.exists():
            raw = p.read_text(errors="replace")
            parts.append(f"\n{name} ({p.stat().st_size} bytes):\n{raw[:9000]}")
elif kind == "ipa":
    manifest_path = Path("work/ipa-manifest.json")
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        main = manifest.get("main", {})
        parts += [
            f"Bundle ID: {main.get('bundle_id')}",
            f"Bundle name: {main.get('bundle_name')}",
            f"Version: {main.get('version')}",
            f"Main Mach-O: {main.get('executable')}",
            f"Bundled dylibs discovered (not yet decompiled): {len(manifest.get('libraries', []))}",
        ]
    session_summary = reports / "ghidra-session-summary.json"
    if session_summary.exists():
        parts.append("\\nPersistent REA/Ghidra session summary:\\n" + session_summary.read_text(errors="replace")[:6000])
    doctor = reports / "ghidra-doctor.json"
    if doctor.exists():
        parts.append("\nGhidra provider diagnostics:\n" + doctor.read_text(errors="replace")[:6000])
    for p in sorted(reports.glob("ghidra-*.json")):
        raw = p.read_text(errors="replace")
        parts.append(f"\n{p.name} ({p.stat().st_size} bytes):\n{raw[:12000]}")
parts.append("\nFull evidence is attached to the GitHub Actions artifact. Decompiled pseudocode is analysis output, not recovered original source code.")
(reports / "summary.txt").write_text("\n".join(parts))
