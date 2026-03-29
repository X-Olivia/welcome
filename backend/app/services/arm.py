"""
Logical arm actions for the guide API (``ArmAction`` enum).

- ``ARM_MOCK=true`` (default): ``execute_arm_action`` logs only; no hardware.
- Route-linked playback of taught poses uses the separate **arm daemon** and
  ``route_arm_direction`` + ``arm_daemon_client`` (not this module’s presets).

Future: map ``ArmAction`` to joint targets or call ``arm_driver`` over IPC.
"""

import logging
from typing import Any

from app.config import settings
from app.models.schemas import ArmAction

logger = logging.getLogger(__name__)

# Logical action -> placeholder joint target or taught preset name.
HARDCODED_PRESETS: dict[ArmAction, dict[str, Any]] = {
    ArmAction.point_left: {"label": "preset_point_left", "note": "TODO: fill in SO101 joint angles or a taught preset name"},
    ArmAction.point_right: {"label": "preset_point_right", "note": "TODO"},
    ArmAction.point_forward: {"label": "preset_point_forward", "note": "TODO"},
    ArmAction.wave: {"label": "preset_wave", "note": "TODO"},
    ArmAction.idle: {"label": "preset_idle", "note": "TODO"},
}


def resolve_preset(action: ArmAction) -> dict[str, Any]:
    return HARDCODED_PRESETS.get(action, HARDCODED_PRESETS[ArmAction.idle])


def execute_arm_action(action: ArmAction) -> dict[str, Any]:
    preset = resolve_preset(action)
    if settings.arm_mock:
        logger.info("[ARM MOCK] action=%s preset=%s", action.value, preset)
        return {"ok": True, "mock": True, "action": action.value, "preset": preset}
    # Placeholder for the physical arm branch, for example by calling arm_driver via subprocess or ZMQ.
    logger.warning("arm_mock=False but no hardware sender is implemented yet; logging only")
    return {"ok": True, "mock": False, "action": action.value, "preset": preset}
