"""Small per-process rate limiter for public ULTRON endpoints."""
from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request

_EVENTS: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_LOCK = Lock()


def enforce_public_limit(request: Request, scope: str, limit: int = 20, window_seconds: int = 60) -> None:
    host = request.client.host if request.client else "unknown"
    key = (scope, host)
    now = monotonic()
    with _LOCK:
        events = _EVENTS[key]
        while events and now - events[0] >= window_seconds:
            events.popleft()
        if len(events) >= limit:
            raise HTTPException(status_code=429, detail="Limite temporário atingido. Aguarde um minuto e tente novamente.")
        events.append(now)
        if len(_EVENTS) > 4096:
            stale = [item for item, queue in _EVENTS.items() if not queue or now - queue[-1] > window_seconds * 2]
            for item in stale:
                _EVENTS.pop(item, None)
