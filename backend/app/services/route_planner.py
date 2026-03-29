from __future__ import annotations

import heapq
import json
import math
from functools import lru_cache
from pathlib import Path

from app.models.schemas import MapPoint, PlaceCard
from app.services.campus_data import place_anchor_point_id

Coord = tuple[int, int]

_MAP_DIR = Path(__file__).resolve().parents[2] / "map"
_CENTERLINE_PATH = _MAP_DIR / "campus_marked_centerline_pixels.json"
_POINTS_PATH = _MAP_DIR / "campus_points_full.json"

# Must match frontend `guideStation` in `frontend/src/campusMap.ts` (LocationMarker / AI guide icon).
_GUIDE_STATION_ID = "IEB (30)"


@lru_cache
def _load_centerline_pixels() -> tuple[Coord, ...]:
    with open(_CENTERLINE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return tuple((int(x), int(y)) for x, y in data["centerline_pixels"])


@lru_cache
def _centerline_set() -> set[Coord]:
    return set(_load_centerline_pixels())


@lru_cache
def _load_map_points() -> dict[str, Coord]:
    with open(_POINTS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {
        str(point["id"]): (int(point["x"]), int(point["y"]))
        for point in data["points"]
    }


def _distance(a: Coord, b: Coord) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


@lru_cache(maxsize=32768)
def _neighbors(node: Coord) -> tuple[Coord, ...]:
    x, y = node
    pixels = _centerline_set()
    neighbors: list[Coord] = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nxt = (x + dx, y + dy)
            if nxt in pixels:
                neighbors.append(nxt)
    return tuple(neighbors)


@lru_cache
def _nearest_centerline(coord: Coord) -> Coord:
    best = None
    best_dist = float("inf")
    for pixel in _load_centerline_pixels():
        dist_sq = (pixel[0] - coord[0]) ** 2 + (pixel[1] - coord[1]) ** 2
        if dist_sq < best_dist:
            best = pixel
            best_dist = dist_sq
    if best is None:
        raise RuntimeError("No walkable centerline pixels were found.")
    return best


def _normalize_step(dx: int, dy: int) -> Coord:
    if dx == 0 and dy == 0:
        return (0, 0)
    return (0 if dx == 0 else int(dx / abs(dx)), 0 if dy == 0 else int(dy / abs(dy)))


def _simplify_path(points: list[Coord]) -> list[Coord]:
    if len(points) <= 2:
        return points

    simplified: list[Coord] = [points[0]]
    prev_step = _normalize_step(points[1][0] - points[0][0], points[1][1] - points[0][1])

    for idx in range(1, len(points) - 1):
        curr_step = _normalize_step(
            points[idx + 1][0] - points[idx][0],
            points[idx + 1][1] - points[idx][1],
        )
        if curr_step != prev_step:
            simplified.append(points[idx])
            prev_step = curr_step

    simplified.append(points[-1])
    return simplified


def _reconstruct(came_from: dict[Coord, Coord | None], current: Coord) -> list[Coord]:
    path = [current]
    while current in came_from and came_from[current] is not None:
        current = came_from[current]  # type: ignore[assignment]
        path.append(current)
    path.reverse()
    return path


@lru_cache(maxsize=128)
def _astar(start: Coord, goal: Coord) -> tuple[Coord, ...]:
    open_heap: list[tuple[float, float, Coord]] = []
    heapq.heappush(open_heap, (_distance(start, goal), 0.0, start))

    came_from: dict[Coord, Coord | None] = {start: None}
    g_score: dict[Coord, float] = {start: 0.0}
    closed: set[Coord] = set()

    while open_heap:
        _, current_g, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        if current == goal:
            return tuple(_reconstruct(came_from, current))
        closed.add(current)

        for neighbor in _neighbors(current):
            tentative_g = current_g + _distance(current, neighbor)
            if tentative_g >= g_score.get(neighbor, float("inf")):
                continue
            came_from[neighbor] = current
            g_score[neighbor] = tentative_g
            f_score = tentative_g + _distance(neighbor, goal)
            heapq.heappush(open_heap, (f_score, tentative_g, neighbor))

    raise RuntimeError(f"No path was found from {start} to {goal}.")


def _path_distance(path: list[Coord]) -> float:
    if len(path) < 2:
        return 0.0
    return sum(_distance(path[i], path[i + 1]) for i in range(len(path) - 1))


def _logical_place_anchor(place_id: str) -> Coord | None:
    map_point_id = place_anchor_point_id(place_id)
    if not map_point_id:
        return None
    return _load_map_points().get(map_point_id)


def guide_station() -> Coord:
    station = _load_map_points().get(_GUIDE_STATION_ID)
    if not station:
        raise RuntimeError("The guide station start coordinate is not configured.")
    return station


def attach_place_coordinates(places: list[PlaceCard]) -> list[PlaceCard]:
    """Attach map anchor pixel coordinates to each logical place card."""

    enriched: list[PlaceCard] = []
    for place in places:
        anchor = _logical_place_anchor(place.id)
        if anchor is None:
            enriched.append(place)
            continue
        enriched.append(place.model_copy(update={"x": anchor[0], "y": anchor[1]}))
    return enriched


def build_route_polyline(places: list[PlaceCard]) -> tuple[list[MapPoint], float]:
    """Build a multi-stop real route polyline over the extracted centerline pixels."""

    if not places:
        return [], 0.0

    current_anchor = guide_station()
    current_node = _nearest_centerline(current_anchor)
    merged_path: list[Coord] = [current_anchor]
    if current_node != current_anchor:
        merged_path.append(current_node)

    total_distance = 0.0

    for place in places:
        anchor = _logical_place_anchor(place.id)
        if anchor is None:
            continue

        goal_node = _nearest_centerline(anchor)
        segment = list(_astar(current_node, goal_node))
        total_distance += _path_distance(segment)

        if segment:
            if merged_path[-1] == segment[0]:
                merged_path.extend(segment[1:])
            else:
                merged_path.extend(segment)

        if merged_path[-1] != anchor:
            merged_path.append(anchor)

        current_anchor = anchor
        current_node = goal_node

    simplified = _simplify_path(merged_path)
    return [MapPoint(x=x, y=y) for x, y in simplified], total_distance
