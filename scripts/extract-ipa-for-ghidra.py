#!/usr/bin/env python3
import json, plistlib, sys, zipfile
from pathlib import Path, PurePosixPath

source = Path(sys.argv[1])
destination = Path(sys.argv[2])
destination.mkdir(parents=True, exist_ok=True)
MAX_TOTAL = 1_500_000_000
MAX_ENTRIES = 50000
MAGICS = {
    bytes.fromhex(x) for x in (
        "feedface", "cefaedfe", "feedfacf", "cffaedfe",
        "cafebabe", "bebafeca", "cafebabf", "bfbafeca",
    )
}
def is_macho(path):
    try:
        with path.open("rb") as f:
            return f.read(4) in MAGICS
    except OSError:
        return False

with zipfile.ZipFile(source) as archive:
    entries = archive.infolist()
    if len(entries) > MAX_ENTRIES:
        raise SystemExit("IPA has too many ZIP entries.")
    total = sum(item.file_size for item in entries)
    if total > MAX_TOTAL:
        raise SystemExit("IPA expands beyond the 1.5 GB safety limit.")
    for item in entries:
        name = item.filename
        posix = PurePosixPath(name)
        if posix.is_absolute() or ".." in posix.parts or "\\" in name:
            raise SystemExit("Unsafe ZIP path in IPA.")
        if not name.startswith("Payload/"):
            continue
        mode = (item.external_attr >> 16) & 0o170000
        if mode == 0o120000:
            raise SystemExit("Symbolic links are not accepted in IPA archives.")
        if item.is_dir():
            continue
        out = destination.joinpath(*posix.parts)
        out.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(item) as src, out.open("wb") as dst:
            while True:
                block = src.read(1024 * 1024)
                if not block: break
                dst.write(block)

apps = sorted((destination / "Payload").glob("*.app"))
if not apps:
    raise SystemExit("No Payload/*.app bundle found in the IPA.")
records = []
for app in apps:
    plist_path = app / "Info.plist"
    if not plist_path.is_file():
        continue
    info = plistlib.loads(plist_path.read_bytes())
    executable_name = info.get("CFBundleExecutable")
    if not isinstance(executable_name, str) or not executable_name or "/" in executable_name:
        continue
    executable = app / executable_name
    if not executable.is_file() or not is_macho(executable):
        continue
    records.append({
        "bundle_id": info.get("CFBundleIdentifier"),
        "bundle_name": info.get("CFBundleName"),
        "executable": str(executable.resolve()),
        "app_bundle": str(app.resolve()),
        "version": info.get("CFBundleShortVersionString"),
    })
if not records:
    raise SystemExit("No Mach-O app executable was found in Payload/*.app.")
# Analyze the main app binary and at most four bundled dynamic libraries.
main = records[0]
libraries = []
for app in apps:
    for path in app.rglob("*.dylib"):
        if is_macho(path):
            libraries.append(str(path.resolve()))
            if len(libraries) >= 4: break
    if len(libraries) >= 4: break
manifest = {"apps": records, "main": main, "libraries": libraries}
Path(destination / "ipa-manifest.json").write_text(json.dumps(manifest, indent=2))
print('IPA validated; app executable and bundled Mach-O libraries identified.')
