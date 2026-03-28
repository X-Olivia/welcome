from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Intent(str, Enum):
    wayfinding = "wayfinding"
    interest_tour = "interest_tour"
    unclear = "unclear"


class ArmAction(str, Enum):
    """与 SO-ARM101 示教/关节姿态对应的逻辑动作名；硬件层再映射到具体角度。"""

    point_left = "point_left"
    point_right = "point_right"
    point_forward = "point_forward"
    wave = "wave"
    idle = "idle"


class NLUResult(BaseModel):
    intent: Intent
    target_place_id: str | None = None
    interest_theme_id: str | None = None
    confidence_note: str | None = None


class GuideRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class PlaceCard(BaseModel):
    id: str
    name_zh: str
    blurb: str


class GuideResponse(BaseModel):
    intent: Intent
    reply_zh: str
    arm_action: ArmAction
    places: list[PlaceCard] = Field(default_factory=list)
    route_summary_zh: str | None = None
    mobile_url: str | None = None
    qr_data_url: str | None = None
    debug: dict[str, Any] | None = None
