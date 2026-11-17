"""Low-overhead process memory diagnostics for constrained deployments."""
from __future__ import annotations

from pathlib import Path


def parse_rss_bytes(status_text: str) -> int | None:
    """Parse Linux VmRSS from /proc/self/status without extra dependencies."""
    for line in status_text.splitlines():
        if line.startswith("VmRSS:"):
            fields = line.split()
            if len(fields) >= 2 and fields[1].isdigit():
                unit = fields[2].lower() if len(fields) > 2 else "kb"
                value = int(fields[1])
                if unit == "kb":
                    return value * 1024
                if unit == "b":
                    return value
    return None


def memory_snapshot(budget_mb: int = 512) -> dict:
    budget_mb = max(64, min(int(budget_mb), 8192))
    try:
        status_text = Path("/proc/self/status").read_text(encoding="ascii")
        rss_bytes = parse_rss_bytes(status_text)
    except (OSError, UnicodeError):
        rss_bytes = None

    budget_bytes = budget_mb * 1024 * 1024
    used_percent = round((rss_bytes / budget_bytes) * 100, 1) if rss_bytes is not None else None
    return {
        "rss_bytes": rss_bytes,
        "budget_bytes": budget_bytes,
        "budget_mb": budget_mb,
        "used_percent": used_percent,
        "pressure": (
            "unknown" if used_percent is None
            else "critical" if used_percent >= 90
            else "high" if used_percent >= 75
            else "normal"
        ),
        "source": "/proc/self/status" if rss_bytes is not None else "unavailable",
    }
