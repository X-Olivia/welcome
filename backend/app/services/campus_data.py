from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.models.schemas import PlaceCard

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "campus.yaml"


def _normalize_token(text: str) -> str:
    return re.sub(r"[\s\-_()（）]+", "", text.strip().lower())


def _is_ascii_token(text: str) -> bool:
    return bool(text) and all(ord(ch) < 128 for ch in text)


@lru_cache
def load_campus() -> dict[str, Any]:
    with open(_DATA_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache
def place_catalog() -> dict[str, dict[str, Any]]:
    return load_campus().get("places", {})


@lru_cache
def theme_catalog() -> dict[str, dict[str, Any]]:
    return load_campus().get("themes", {})


def _variants(entry_id: str, entry: dict[str, Any]) -> list[str]:
    variants = [entry_id]
    for key in ("name_zh", "name_en"):
        value = entry.get(key)
        if value:
            variants.append(str(value))
    variants.extend(str(alias) for alias in entry.get("aliases") or [])
    return variants


@lru_cache
def _place_alias_index() -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for place_id, entry in place_catalog().items():
        for variant in _variants(place_id, entry):
            token = _normalize_token(variant)
            if not token:
                continue
            index.setdefault(token, [])
            if place_id not in index[token]:
                index[token].append(place_id)
    return index


@lru_cache
def _theme_alias_index() -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for theme_id, entry in theme_catalog().items():
        for variant in _variants(theme_id, entry):
            token = _normalize_token(variant)
            if not token:
                continue
            index.setdefault(token, [])
            if theme_id not in index[token]:
                index[token].append(theme_id)
    return index


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def resolve_place_token(token: str) -> str | None:
    normalized = _normalize_token(token)
    matches = _place_alias_index().get(normalized, [])
    if len(matches) == 1:
        return matches[0]

    fuzzy_matches: list[str] = []
    for alias, place_ids in _place_alias_index().items():
        if normalized and (normalized in alias or alias in normalized):
            fuzzy_matches.extend(place_ids)
    fuzzy_matches = _dedupe(fuzzy_matches)
    if len(fuzzy_matches) == 1:
        return fuzzy_matches[0]
    return None


def resolve_theme_token(token: str) -> str | None:
    normalized = _normalize_token(token)
    matches = _theme_alias_index().get(normalized, [])
    if len(matches) == 1:
        return matches[0]

    fuzzy_matches: list[str] = []
    for alias, theme_ids in _theme_alias_index().items():
        if normalized and (normalized in alias or alias in normalized):
            fuzzy_matches.extend(theme_ids)
    fuzzy_matches = _dedupe(fuzzy_matches)
    if len(fuzzy_matches) == 1:
        return fuzzy_matches[0]
    return None


def _alias_in_text(alias: str, raw_text: str, normalized_text: str) -> bool:
    if not alias:
        return False
    if _is_ascii_token(alias):
        pattern = rf"(?<![a-z0-9]){re.escape(alias.lower())}(?![a-z0-9])"
        return re.search(pattern, raw_text.lower()) is not None
    return _normalize_token(alias) in normalized_text


def _alias_position(alias: str, raw_text: str, normalized_text: str) -> int | None:
    if not alias:
        return None
    if _is_ascii_token(alias):
        pattern = rf"(?<![a-z0-9]){re.escape(alias.lower())}(?![a-z0-9])"
        match = re.search(pattern, raw_text.lower())
        return match.start() if match else None

    normalized_alias = _normalize_token(alias)
    if not normalized_alias:
        return None
    position = normalized_text.find(normalized_alias)
    return position if position >= 0 else None


def extract_place_mentions(text: str) -> list[str]:
    """Extract place ids in the order they appear in user text."""

    raw_text = text.strip()
    normalized_text = _normalize_token(raw_text)
    hits: list[tuple[int, int, str]] = []
    for place_id, entry in place_catalog().items():
        best_position: int | None = None
        best_length = 0
        for alias in _variants(place_id, entry):
            position = _alias_position(alias, raw_text, normalized_text)
            if position is None:
                continue
            alias_length = len(_normalize_token(alias))
            if best_position is None or position < best_position or (
                position == best_position and alias_length > best_length
            ):
                best_position = position
                best_length = alias_length
        if best_position is not None:
            hits.append((best_position, -best_length, place_id))
    hits.sort()
    return [place_id for _, _, place_id in hits]


def extract_theme_mentions(text: str) -> list[str]:
    """Extract theme ids in the order they appear in user text."""

    raw_text = text.strip()
    normalized_text = _normalize_token(raw_text)
    hits: list[tuple[int, int, str]] = []
    for theme_id, entry in theme_catalog().items():
        best_position: int | None = None
        best_length = 0
        for alias in _variants(theme_id, entry):
            position = _alias_position(alias, raw_text, normalized_text)
            if position is None:
                continue
            alias_length = len(_normalize_token(alias))
            if best_position is None or position < best_position or (
                position == best_position and alias_length > best_length
            ):
                best_position = position
                best_length = alias_length
        if best_position is not None:
            hits.append((best_position, -best_length, theme_id))
    hits.sort()
    return [theme_id for _, _, theme_id in hits]


def build_place_card(place_id: str) -> PlaceCard | None:
    entry = place_catalog().get(place_id)
    if not entry:
        return None
    english_name = str(entry.get("name_en") or entry.get("name_zh") or place_id)
    english_blurb = str(entry.get("blurb_en") or f"Explore {english_name} as part of this campus route.")
    return PlaceCard(
        id=place_id,
        name_zh=english_name,
        blurb=english_blurb,
    )


def build_place_cards(place_ids: list[str]) -> list[PlaceCard]:
    cards: list[PlaceCard] = []
    for place_id in place_ids:
        card = build_place_card(place_id)
        if card is not None:
            cards.append(card)
    return cards


def place_direction(place_id: str) -> str:
    return str(place_catalog().get(place_id, {}).get("direction", "forward"))


def place_anchor_point_id(place_id: str) -> str | None:
    entry = place_catalog().get(place_id)
    if not entry:
        return None
    value = entry.get("map_point_id")
    return str(value) if value else None


def theme_waypoints(theme_id: str) -> list[str]:
    entry = theme_catalog().get(theme_id)
    if not entry:
        return []
    return [str(pid) for pid in entry.get("ordered_waypoints") or []]


def theme_intro(theme_id: str) -> str | None:
    entry = theme_catalog().get(theme_id)
    if not entry:
        return None
    intro = entry.get("intro_en")
    if intro:
        return str(intro)
    theme_name = str(entry.get("name_en") or entry.get("name_zh") or theme_id).strip()
    return f"This route is designed around {theme_name.lower()} and gives you a clear way to explore the campus."


def default_recommendation_theme() -> str:
    for theme_id, entry in theme_catalog().items():
        if entry.get("default_recommendation"):
            return theme_id
    return "first_visit"


def default_recommendation_waypoints() -> list[str]:
    return theme_waypoints(default_recommendation_theme())


def theme_waypoints_for_ids(theme_ids: list[str]) -> list[str]:
    waypoints: list[str] = []
    for theme_id in theme_ids:
        waypoints.extend(theme_waypoints(theme_id))
    return _dedupe(waypoints)


def list_place_summaries_for_prompt() -> str:
    lines: list[str] = []
    for place_id, entry in place_catalog().items():
        aliases = "、".join(entry.get("aliases") or [])
        name_en = entry.get("name_en", "")
        lines.append(
            f"- place_id={place_id} zh={entry['name_zh']} en={name_en} aliases=[{aliases}]"
        )
    for theme_id, entry in theme_catalog().items():
        aliases = "、".join(entry.get("aliases") or [])
        ordered = ",".join(entry.get("ordered_waypoints") or [])
        lines.append(
            f"- theme_id={theme_id} zh={entry['name_zh']} aliases=[{aliases}] ordered_waypoints=[{ordered}]"
        )
    return "\n".join(lines)
