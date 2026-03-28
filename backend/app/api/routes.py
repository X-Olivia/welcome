from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile

from app.config import settings
from app.models.schemas import (
    GuideRequest,
    GuideResponse,
    MultiRouteRequest,
    RoutePlanResponse,
    RouteRequest,
    SpeechRequest,
    VoiceTranscriptResponse,
)
from app.services.arm import execute_arm_action
from app.services.assemblyai import transcribe_audio_bytes
from app.services.cartesia import synthesize_speech_bytes
from app.services.decision import plan_multi_stop_route, plan_route_to_destination, run_guide_pipeline
from app.services.session_store import get as session_get

router = APIRouter()


@router.get("/session/{token}")
def get_session(token: str) -> dict:
    data = session_get(token)
    if not data:
        raise HTTPException(status_code=404, detail="This session has expired or does not exist.")
    return data


@router.post("/guide", response_model=GuideResponse)
def post_guide(body: GuideRequest) -> GuideResponse:
    result = run_guide_pipeline(body.message)
    arm_result = execute_arm_action(result.arm_action)
    if result.debug is not None:
        result.debug["arm"] = arm_result
    else:
        result.debug = {"arm": arm_result}
    return result


@router.post("/route", response_model=RoutePlanResponse)
def post_route(body: RouteRequest) -> RoutePlanResponse:
    try:
        return plan_route_to_destination(body.destination)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/route/multi", response_model=RoutePlanResponse)
def post_multi_route(body: MultiRouteRequest) -> RoutePlanResponse:
    try:
        return plan_multi_stop_route(body.waypoints, body.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/voice/transcribe", response_model=VoiceTranscriptResponse)
async def post_voice_transcribe(
    audio: UploadFile = File(...),
    language: str | None = Form(default=None),
) -> VoiceTranscriptResponse:
    try:
        audio_bytes = await audio.read()
        text = await transcribe_audio_bytes(audio_bytes, language_code=language)
        return VoiceTranscriptResponse(text=text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Voice transcription failed: {exc}") from exc


@router.post("/voice/speak")
async def post_voice_speak(body: SpeechRequest) -> Response:
    try:
        audio_bytes = await synthesize_speech_bytes(
            body.text,
            language=body.language,
            speed=body.speed,
        )
        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={"Cache-Control": "no-store"},
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Voice synthesis failed: {exc}") from exc


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/debug/config")
def debug_config() -> dict[str, object]:
    return {
        "openai_api_key_configured": bool(settings.openai_api_key),
        "assemblyai_api_key_configured": bool(settings.assemblyai_api_key),
        "cartesia_api_key_configured": bool(settings.cartesia_api_key),
        "openai_base_url": settings.openai_base_url,
        "assemblyai_base_url": settings.assemblyai_base_url,
        "cartesia_base_url": settings.cartesia_base_url,
        "cartesia_language": settings.cartesia_language,
        "public_base_url": settings.public_base_url,
    }
