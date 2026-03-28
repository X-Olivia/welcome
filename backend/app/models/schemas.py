from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Intent(str, Enum):
    route = "route"
    tour = "tour"
    recommend_tour = "recommend_tour"
    clarification = "clarification"


class ArmAction(str, Enum):
    """Logical arm action names that the hardware layer can map to actual poses."""

    point_left = "point_left"
    point_right = "point_right"
    point_forward = "point_forward"
    wave = "wave"
    idle = "idle"


class NLUResult(BaseModel):
    intent: Intent
    places: list[str] = Field(default_factory=list)
    ordered_waypoints: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    reply_text: str = ""
    confidence: float | None = None
    needs_clarification: bool = False
    clarification_question: str | None = None
    debug: dict[str, Any] | None = None


class GuideRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class RouteRequest(BaseModel):
    destination: str = Field(..., min_length=1, max_length=200)


class MultiRouteRequest(BaseModel):
    waypoints: list[str] = Field(..., min_length=1, max_length=12)
    mode: Intent = Intent.tour


class SpeechRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=600)
    language: str = Field(default="en", min_length=2, max_length=10)
    speed: float | None = Field(default=None, ge=0.5, le=2.0)


class PlaceCard(BaseModel):
    id: str
    name_zh: str
    blurb: str
    x: int | None = None
    y: int | None = None


class MapPoint(BaseModel):
    x: int
    y: int


class GuideResponse(BaseModel):
    intent: Intent
    reply_zh: str
    arm_action: ArmAction
    places: list[PlaceCard] = Field(default_factory=list)
    route_summary_zh: str | None = None
    route_polyline: list[MapPoint] = Field(default_factory=list)
    route_distance_px: float | None = None
    mobile_url: str | None = None
    qr_data_url: str | None = None
    debug: dict[str, Any] | None = None


class RoutePlanResponse(BaseModel):
    mode: Intent
    summary: str
    arm_action: ArmAction
    waypoints: list[PlaceCard] = Field(default_factory=list)
    path: list[MapPoint] = Field(default_factory=list)
    route_distance_px: float | None = None
    share_url: str | None = None


class VoiceTranscriptResponse(BaseModel):
    text: str
    duration_ms: int | None = None
