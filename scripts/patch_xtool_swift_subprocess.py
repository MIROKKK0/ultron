#!/usr/bin/env python3
"""Apply a narrow Swift 6.4 compatibility fix to xtool's pinned swift-subprocess checkout.

Swift 6.4.3 does not expose Data.bytes on Darwin. The dependency already accepts
[UInt8] through the same AsyncIO write path, so Array(data) preserves the bytes
without changing subprocess behavior. This only edits the ephemeral CI checkout.
"""
from __future__ import annotations

import sys
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_swift_subprocess.py <xtool-checkout>")

root = Path(sys.argv[1])
matches = list(root.glob(".build/checkouts/swift-subprocess/Sources/Subprocess/SubprocessFoundation/Input+Foundation.swift"))
if len(matches) != 1:
    raise SystemExit(f"expected one swift-subprocess source file, found {len(matches)}")

path = matches[0]
source = path.read_text()
old = "return try await self.write(data.bytes, to: diskIO, for: processIdentifier)"
new = "return try await self.write(Array(data), to: diskIO, for: processIdentifier)"

if new in source:
    print("swift-subprocess compatibility patch already present")
elif old in source:
    path.write_text(source.replace(old, new, 1))
    print("patched swift-subprocess Data input for Swift 6.4.3")
else:
    raise SystemExit("upstream swift-subprocess source changed; refusing an unverified patch")
