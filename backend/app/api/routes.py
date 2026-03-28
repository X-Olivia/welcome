from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    GuideRequest,
    GuideResponse,
    MultiRouteRequest,
    RoutePlanResponse,
    RouteRequest,
)
from app.services.arm import execute_arm_action
from app.services.decision import plan_multi_stop_route, plan_route_to_destination, run_guide_pipeline
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


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
