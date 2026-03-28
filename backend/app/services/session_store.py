import time
from typing import Any

_STORE: dict[str, tuple[float, dict[str, Any]]] = {}
_TTL_SEC = 3600


def put(payload: dict[str, Any]) -> str:
    import secrets

    token = secrets.token_urlsafe(12)
    _STORE[token] = (time.time(), payload)
    _purge()
    return token


def get(token: str) -> dict[str, Any] | None:
    _purge()
    item = _STORE.get(token)
    if not item:
        return None
    return item[1]


def _purge() -> None:
    now = time.time()
    dead = [k for k, (ts, _) in _STORE.items() if now - ts > _TTL_SEC]
    for k in dead:
        del _STORE[k]
