"""
Map the first segment of a route polyline to an 8-way compass ``action_key``.

Convention: map **north** is toward decreasing pixel **y** (screen up). For segment
vector ``(dx, dy)``, bearing = ``atan2(dx, -dy)`` with 0° = north, increasing
clockwise (east = 90°). Keys match ``record_leader_poses.py`` / recording JSON.

Use ``north_offset_deg`` in settings when the artwork’s north does not match this.
"""

from __future__ import annotations

import math
from typing import Protocol, Sequence

# Sector centers at 0°, 45°, …, 315° (clockwise from north).
EIGHT_DIRECTION_KEYS: tuple[str, ...] = (
    "point_north",
    "point_northeast",
    "point_east",
    "point_southeast",
    "point_south",
    "point_southwest",
    "point_west",
    "point_northwest",
)


class _XY(Protocol):
    x: int
    y: int


def polyline_to_action_key(
    polyline: Sequence[_XY],
    *,
    min_segment_px: float = 3.0,
    north_offset_deg: float = 0.0,
) -> str | None:
    """First edge with length >= ``min_segment_px`` → 8-way key; ``None`` if unavailable."""

    if len(polyline) < 2:
        return None

    for i in range(len(polyline) - 1):
        a, b = polyline[i], polyline[i + 1]
        dx = float(b.x - a.x)
        dy = float(b.y - a.y)
        dist = math.hypot(dx, dy)
        if dist >= min_segment_px:
            bearing_deg = (math.degrees(math.atan2(dx, -dy)) + 360.0) % 360.0
            adj = (bearing_deg + north_offset_deg + 360.0) % 360.0
            idx = int((adj + 22.5) % 360.0 // 45) % 8
            return EIGHT_DIRECTION_KEYS[idx]
    return None
