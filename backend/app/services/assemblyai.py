from __future__ import annotations

import asyncio
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _headers() -> dict[str, str]:
    if not settings.assemblyai_api_key:
        raise RuntimeError("AssemblyAI is not configured. Please set ASSEMBLYAI_API_KEY.")
    return {"Authorization": settings.assemblyai_api_key}


async def transcribe_audio_bytes(audio_bytes: bytes, *, language_code: str | None = None) -> str:
    """Upload recorded audio to AssemblyAI and poll until transcript completes."""

    if not audio_bytes:
        raise RuntimeError("Audio content is empty.")

    timeout = httpx.Timeout(30.0, connect=10.0)
    base_url = settings.assemblyai_base_url.rstrip("/")
    headers = _headers()

    async with httpx.AsyncClient(timeout=timeout) as client:
        upload_resp = await client.post(
            f"{base_url}/upload",
            headers={**headers, "Content-Type": "application/octet-stream"},
            content=audio_bytes,
        )
        upload_resp.raise_for_status()
        upload_url = upload_resp.json().get("upload_url")
        if not upload_url:
            raise RuntimeError("AssemblyAI upload succeeded but did not return an upload_url.")

        transcript_payload = {
            "audio_url": upload_url,
            "speech_models": ["universal-2"],
        }
        if language_code:
            transcript_payload["language_code"] = language_code
        else:
            transcript_payload["language_detection"] = True

        transcript_resp = await client.post(
            f"{base_url}/transcript",
            headers=headers,
            json=transcript_payload,
        )
        transcript_resp.raise_for_status()
        transcript_id = transcript_resp.json().get("id")
        if not transcript_id:
            raise RuntimeError("AssemblyAI did not return a transcription job id.")

        for _ in range(settings.assemblyai_poll_attempts):
            await asyncio.sleep(settings.assemblyai_poll_interval_ms / 1000)
            poll_resp = await client.get(f"{base_url}/transcript/{transcript_id}", headers=headers)
            poll_resp.raise_for_status()
            data = poll_resp.json()
            status = data.get("status")

            if status == "completed":
                return str(data.get("text") or "").strip()
            if status == "error":
                raise RuntimeError(str(data.get("error") or "AssemblyAI transcription failed."))

        raise RuntimeError("AssemblyAI transcription timed out. Please try again.")
