import io
import logging
from urllib.parse import urlencode

from app.config import settings
from app.models.schemas import GuideResponse, Intent, NLUResult, PlaceCard, RoutePlanResponse
from app.services.campus_data import resolve_place_token
from app.services.content import compose_reply, compose_route_plan
from app.services.nlu import run_nlu
from app.services.route_planner import attach_place_coordinates, build_route_polyline
from app.services.session_store import put as session_put

logger = logging.getLogger(__name__)


def _qr_data_url(url: str) -> str | None:
    try:
        import base64

        import qrcode
    except ImportError:
        logger.warning("qrcode is not installed; skipping QR generation. Run: pip install 'qrcode[pil]'")
        return None
    try:
        buf = io.BytesIO()
        img = qrcode.make(url)
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        logger.warning("QR generation failed: %s", e)
        return None


def build_share_url(intent: Intent, waypoint_ids: list[str]) -> str | None:
    if not waypoint_ids:
        return None
    query = urlencode({"mode": intent.value, "waypoints": ",".join(waypoint_ids)})
    return f"{settings.public_base_url.rstrip('/')}/mobile?{query}"


def _build_guide_response(
    *,
    intent: Intent,
    places: list[PlaceCard],
    route_summary: str | None,
    reply_zh: str,
    arm_action,
    debug: dict | None = None,
) -> GuideResponse:
    places = attach_place_coordinates(places)
    route_polyline = []
    route_distance_px = 0.0
    route_error: str | None = None
    try:
        route_polyline, route_distance_px = build_route_polyline(places)
    except Exception as e:
        logger.warning("Route planning failed: %s", e)
        route_error = str(e)

    session_payload = {
        "reply_zh": reply_zh,
        "intent": intent.value,
        "places": [p.model_dump() for p in places],
        "route_summary_zh": route_summary,
        "route_polyline": [p.model_dump() for p in route_polyline],
        "route_distance_px": route_distance_px,
        "arm_action": arm_action.value,
    }
    token = session_put(session_payload)
    waypoint_ids = [place.id for place in places]
    mobile_url = build_share_url(intent, waypoint_ids)
    qr_data_url = _qr_data_url(mobile_url) if mobile_url else None

    merged_debug = dict(debug or {})
    merged_debug["session_token"] = token
    merged_debug["legacy_mobile_url"] = f"{settings.public_base_url.rstrip('/')}/m/{token}"
    merged_debug["route"] = {
        "polyline_points": len(route_polyline),
        "distance_px": route_distance_px,
        "error": route_error,
    }

    return GuideResponse(
        intent=intent,
        reply_zh=reply_zh,
        arm_action=arm_action,
        places=places,
        route_summary_zh=route_summary,
        route_polyline=route_polyline,
        route_distance_px=route_distance_px,
        mobile_url=mobile_url,
        qr_data_url=qr_data_url,
        debug=merged_debug,
    )


def run_guide_pipeline(message: str) -> GuideResponse:
    nlu: NLUResult = run_nlu(message)
    places, route_summary, arm_action, effective_intent = compose_reply(nlu)

    if route_summary:
        reply_zh = route_summary
    else:
        reply_zh = "All set."

    return _build_guide_response(
        intent=effective_intent,
        places=places,
        route_summary=route_summary,
        reply_zh=reply_zh,
        arm_action=arm_action,
        debug={
            "nlu": nlu.model_dump(),
        },
    )


def _normalize_waypoint_ids(raw_waypoints: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_waypoint in raw_waypoints:
        place_id = resolve_place_token(raw_waypoint)
        if not place_id or place_id in seen:
            continue
        normalized.append(place_id)
        seen.add(place_id)
    return normalized


def _build_route_plan_response(
    *,
    waypoint_ids: list[str],
    intent: Intent,
    summary: str | None = None,
) -> RoutePlanResponse:
    cards, route_summary, arm_action = compose_route_plan(waypoint_ids, intent, summary)
    cards = attach_place_coordinates(cards)
    path, route_distance_px = build_route_polyline(cards)
    return RoutePlanResponse(
        mode=intent,
        summary=route_summary,
        arm_action=arm_action,
        waypoints=cards,
        path=path,
        route_distance_px=route_distance_px,
        share_url=build_share_url(intent, [card.id for card in cards]),
    )


def plan_route_to_destination(destination: str) -> RoutePlanResponse:
    waypoint_ids = _normalize_waypoint_ids([destination])
    if not waypoint_ids:
        raise ValueError("I could not recognize that destination.")
    return _build_route_plan_response(waypoint_ids=waypoint_ids, intent=Intent.route)


def plan_multi_stop_route(waypoints: list[str], mode: Intent = Intent.tour) -> RoutePlanResponse:
    if mode not in (Intent.route, Intent.tour, Intent.recommend_tour):
        mode = Intent.tour
    waypoint_ids = _normalize_waypoint_ids(waypoints)
    if not waypoint_ids:
        raise ValueError("I could not recognize any routeable waypoints.")
    effective_mode = Intent.route if len(waypoint_ids) == 1 and mode == Intent.route else mode
    return _build_route_plan_response(waypoint_ids=waypoint_ids, intent=effective_mode)
