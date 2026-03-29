"""
Fire-and-forget HTTP client for the local arm daemon (``arm_driver/arm_daemon.py``).

Posts ``{"action_key": ...}`` to ``POST /v1/play`` from a daemon thread so FastAPI
handlers stay non-blocking. Errors are logged only.
"""

from __future__ import annotations

import logging
import threading

import httpx

logger = logging.getLogger(__name__)


def schedule_arm_daemon_play(base_url: str, action_key: str, *, timeout_sec: float) -> None:
    """Spawn a background thread that POSTs ``/v1/play``; never raises to the caller."""

    url = f"{base_url.rstrip('/')}/v1/play"
    timeout = httpx.Timeout(timeout_sec)

    def _run() -> None:
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, json={"action_key": action_key})
                if response.status_code in (200, 202):
                    logger.info(
                        "arm_daemon play accepted: key=%s status=%s", action_key, response.status_code
                    )
                else:
                    logger.warning(
                        "arm_daemon play failed: key=%s status=%s body=%s",
                        action_key,
                        response.status_code,
                        response.text[:500],
                    )
        except Exception:
            logger.exception("arm_daemon request error: key=%s", action_key)

    threading.Thread(target=_run, name="arm-daemon-client", daemon=True).start()
