"""
SO-ARM101（LeRobot）动作层：当前为硬编码映射 + 可选 mock。

后续接入真机时：
- 用 LeRobot Robot 配置连接 SO-ARM101，将 ArmAction 映射到示教关节角或轨迹；
- 或通过独立进程 arm_driver 接收 HTTP/WebSocket，再调用 lerobot。
"""

import logging
from typing import Any

from app.config import settings
from app.models.schemas import ArmAction

logger = logging.getLogger(__name__)

# 逻辑动作 -> 占位「关节目标」或示教名（leader 损坏时可仅打印/记录）
HARDCODED_PRESETS: dict[ArmAction, dict[str, Any]] = {
    ArmAction.point_left: {"label": "preset_point_left", "note": "TODO: 填入 SO101 关节角或示教名"},
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
    # 真机分支占位：例如调用 subprocess 或 ZMQ 到 arm_driver
    logger.warning("arm_mock=False 但未实现硬件发送，仍仅记录")
    return {"ok": True, "mock": False, "action": action.value, "preset": preset}
