from fastapi import APIRouter, HTTPException

from app.models.schemas import GuideRequest, GuideResponse
from app.services.arm import execute_arm_action
from app.services.decision import run_guide_pipeline
from app.services.session_store import get as session_get

router = APIRouter()


@router.get("/session/{token}")
def get_session(token: str) -> dict:
    data = session_get(token)
    if not data:
        raise HTTPException(status_code=404, detail="会话已过期或不存在")
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


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
