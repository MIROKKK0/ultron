#!/usr/bin/env python3
"""Apply narrow Swift 6.4 compatibility fixes to xtool's pinned dependency checkout.

Swift 6.4.3 no longer exposes the Data.mutableBytes convenience used by
swift-crypto 5.0.3 on this code path. Its existing withUnsafeMutableBytes
fallback is compatible and preserves the in-place AEAD operation. The patch
also adapts swift-subprocess Data.bytes to [UInt8]. Only the ephemeral CI
checkout is edited; no vendored dependency is committed to ULTRON.
"""
from __future__ import annotations

import sys
from pathlib import Path


def patch_file(root: Path, relative_path: str, old: str, new: str, label: str) -> None:
    matches = list(root.glob(relative_path))
    if len(matches) != 1:
        raise SystemExit(f"expected one {label} source file, found {len(matches)}")

    path = matches[0]
    source = path.read_text()
    if new in source:
        print(f"{label} compatibility patch already present")
        return
    if old not in source:
        raise SystemExit(f"{label} source changed; refusing an unverified patch")

    # Dependency checkouts may mark vendored sources read-only. Change only
    # this temporary CI copy before applying the narrow compatibility edit.
    path.chmod(path.stat().st_mode | 0o200)
    path.write_text(source.replace(old, new, 1))
    print(f"patched {label} for Swift 6.4.3")


if len(sys.argv) != 2:
    raise SystemExit("usage: patch_xtool_swift_subprocess.py <xtool-checkout>")

root = Path(sys.argv[1])

patch_file(
    root,
    ".build/checkouts/swift-subprocess/Sources/Subprocess/SubprocessFoundation/Input+Foundation.swift",
    "return try await self.write(data.bytes, to: diskIO, for: processIdentifier)",
    "return try await self.write(Array(data), to: diskIO, for: processIdentifier)",
    "swift-subprocess Data input",
)

patch_file(
    root,
    ".build/checkouts/swift-crypto/Sources/CryptoBoringWrapper/AEAD/BoringSSLAEAD.swift",
    """        if #available(visionOS 1.1, *) {
            var outputSpan = output.mutableBytes
            try open(message: &outputSpan, nonce: nonceBytes, tag: tagBytes, authenticatedData: authenticatedData)
        } else {
            // For some reason `Data.mutableBytes` is not available on visionOS 1.0 so we'll bounce through wUSMB.
            try output.withUnsafeMutableBytes { bytes in
                var outputSpan = bytes.mutableBytes
                try open(message: &outputSpan, nonce: nonceBytes, tag: tagBytes, authenticatedData: authenticatedData)
            }
        }""",
    """        try output.withUnsafeMutableBytes { bytes in
            var outputSpan = bytes.mutableBytes
            try open(message: &outputSpan, nonce: nonceBytes, tag: tagBytes, authenticatedData: authenticatedData)
        }""",
    "swift-crypto Data mutable buffer",
)
