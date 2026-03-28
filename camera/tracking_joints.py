"""
多关节协同：把画面偏差 (ex, ey) 分配到 pan / lift / elbow / wrist，使 target 回到中心。
ex、ey 为归一化偏差约 [-1,1]（相对画面半宽/半高）。
"""

from __future__ import annotations

from typing import Any


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def apply_centering_to_action(
    action: dict[str, Any],
    ex: float,
    ey: float,
    *,
    pan_sign: float,
    lift_sign: float,
    max_pan_step: float,
    max_lift_step: float,
    pan_gain: float,
    lift_gain: float,
    dead_zone_h: float,
    dead_zone_v: float,
    # 水平：pan 为主，roll 微调
    share_pan: float = 0.82,
    share_wrist_roll: float = 0.18,
    # 垂直：lift、elbow、wrist_flex 分摊
    share_lift: float = 0.42,
    share_elbow: float = 0.38,
    share_wrist_flex: float = 0.20,
) -> bool:
    """
    就地修改 action 中各 *.pos。若本轮无任何位移则返回 False。
    """
    h = 0.0
    if abs(ex) > dead_zone_h:
        h = pan_sign * clamp(ex, -1.0, 1.0) * max_pan_step * pan_gain
    v = 0.0
    if abs(ey) > dead_zone_v:
        v = lift_sign * clamp(ey, -1.0, 1.0) * max_lift_step * lift_gain

    if h == 0.0 and v == 0.0:
        return False

    action["shoulder_pan.pos"] = float(action["shoulder_pan.pos"]) + h * share_pan
    action["wrist_roll.pos"] = float(action["wrist_roll.pos"]) + h * share_wrist_roll
    action["shoulder_lift.pos"] = float(action["shoulder_lift.pos"]) + v * share_lift
    action["elbow_flex.pos"] = float(action["elbow_flex.pos"]) + v * share_elbow
    action["wrist_flex.pos"] = float(action["wrist_flex.pos"]) + v * share_wrist_flex
    return True
