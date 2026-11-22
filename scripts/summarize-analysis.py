#!/usr/bin/env python3
import json, os, re
from pathlib import Path

kind = os.environ.get("TARGET_TYPE", "unknown")
reports = Path("reports")
reports.mkdir(exist_ok=True)
parts = [f"ULTRON isolated reverse-engineering worker: {kind}"]

def compact_json(path, limit=1800):
    try:
        data = json.loads(path.read_text(errors="replace"))
        if isinstance(data, dict):
            safe = {key: value for key, value in data.items()
                    if key.lower() not in {"source", "source_text", "script_source", "pseudocode", "body", "content", "headers", "cookies", "storage"}}
            text = json.dumps(safe, ensure_ascii=False)
        else:
            text = json.dumps({"type": type(data).__name__, "items": len(data) if isinstance(data, list) else 1}, ensure_ascii=False)
        text = re.sub(r"(?i)(token|secret|password|authorization|api[_-]?key)(\\s*[:=]\\s*)[^,\\s\\\"]+", r"\\1\\2[REDACTED]", text)
        return text[:limit]
    except Exception:
        return f"JSON could not be summarized ({path.stat().st_size} bytes)."

if kind == "site":
    path = reports / "site-session.json"
    if path.exists():
        data = json.loads(path.read_text())
        pages = data.get("pagesVisited", [])
        parts += [
            f"Approved origin: {data.get('requestedOrigin')}",
            f"Initial URL: {data.get('initialUrl')}",
            f"Same-origin pages visited: {len(pages)} (maximum {data.get('maxSameOriginPages', 8)})",
            "Visited pages: " + "; ".join(f"{item.get('title', '')} — {item.get('url', '')}" for item in pages),
            f"Crawl policy: {data.get('crawlPolicy')}",
            "Browser profile: isolated, disposable, no personal cookies",
        ]
    for p in sorted(reports.glob("page-*-inspection.json")):
        parts.append(f"\\n{p.name}: {compact_json(p)}")
    for p in sorted(reports.glob("page-*-bundle-analysis.json")):
        parts.append(f"\\n{p.name}: {compact_json(p)}")
elif kind == "ipa":
    manifest_path = Path("work/ipa-manifest.json")
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        main = manifest.get("main", {})
        parts += [
            f"Bundle ID: {main.get('bundle_id')}",
            f"Bundle name: {main.get('bundle_name')}",
            f"Version: {main.get('version')}",
            f"Main Mach-O: {Path(main.get('executable', '')).name}",
            f"Bundled dylibs discovered (not yet individually analyzed): {len(manifest.get('libraries', []))}",
        ]
    session_summary = reports / "ghidra-session-summary.json"
    if session_summary.exists():
        parts.append("\\nPersistent REA/Ghidra session summary:\\n" + session_summary.read_text(errors="replace")[:6000])
    doctor = reports / "ghidra-doctor.json"
    if doctor.exists():
        parts.append("\\nGhidra provider diagnostics:\\n" + compact_json(doctor, 4000))
    for p in sorted(reports.glob("ghidra-function-*.json")):
        parts.append(f"\\n{p.name}: {compact_json(p, 6500)}")
    for name in ("ghidra-binary_overview.json", "ghidra-list_procedures.json", "ghidra-get_objc_classes.json", "ghidra-get_objc_protocols.json", "ghidra-analyze_swift_types.json", "ghidra-inspect_native_dispatch_metadata.json"):
        p = reports / name
        if p.exists():
            parts.append(f"\\n{name}: {compact_json(p, 3000)}")

parts.append("\\nRaw reports remain only on the ephemeral worker and are not uploaded to the public GitHub repository. This response contains bounded analysis evidence, not recovered original source code.")
(reports / "summary.txt").write_text("\\n".join(parts))
