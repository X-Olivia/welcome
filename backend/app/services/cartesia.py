from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _headers() -> dict[str, str]:
    if not settings.cartesia_api_key:
        raise RuntimeError("Cartesia is not configured. Please set CARTESIA_API_KEY.")
    return {
        "Authorization": f"Bearer {settings.cartesia_api_key}",
        "Cartesia-Version": settings.cartesia_version,
        "Content-Type": "application/json",
    }


async def synthesize_speech_bytes(
    text: str,
    *,
    language: str | None = None,
    speed: float | None = None,
) -> bytes:
    """Generate a short spoken response using Cartesia's bytes endpoint."""

    normalized_text = text.strip()
    if not normalized_text:
        raise RuntimeError("TTS text is empty.")

    timeout = httpx.Timeout(40.0, connect=10.0)
    base_url = settings.cartesia_base_url.rstrip("/")
    payload = {
        "model_id": settings.cartesia_model_id,
        "transcript": normalized_text,
        "voice": {"mode": "id", "id": settings.cartesia_voice_id},
        "output_format": {
            "container": "wav",
            "encoding": "pcm_s16le",
            "sample_rate": 24000,
        },
        "language": language or settings.cartesia_language,
        "generation_config": {
            "speed": speed if speed is not None else settings.cartesia_speed,
            "volume": 1,
        },
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(f"{base_url}/tts/bytes", headers=_headers(), json=payload)
        response.raise_for_status()
        return response.content
