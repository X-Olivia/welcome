from __future__ import annotations

import logging
import re
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, Field

from app.config import settings
from app.models.schemas import Intent, NLUResult
from app.services.campus_data import (
    default_recommendation_theme,
    default_recommendation_waypoints,
    extract_place_mentions,
    extract_theme_mentions,
    list_place_summaries_for_prompt,
    resolve_place_token,
    resolve_theme_token,
    theme_waypoints_for_ids,
)

logger = logging.getLogger(__name__)


class _LLMGuideParse(BaseModel):
    intent: Literal["route", "tour", "recommend_tour", "clarification"]
    places: list[str] = Field(default_factory=list)
    ordered_waypoints: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    reply_text: str = ""
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    needs_clarification: bool = False
    clarification_question: str | None = None


_SYSTEM = """You are the natural-language understanding module for an open-day campus AI guide.
Your job is not to write a long explanation. Your job is to turn the user's request into a stable,
executable, structured guide plan.

You must choose exactly one intent:
- route: the user clearly wants directions to one destination
- tour: the user wants a themed, area-based, or multi-stop campus route
- recommend_tour: the user is vague but clearly wants the system to recommend a route
- clarification: the request cannot be mapped reliably and needs a follow-up question

Output rules:
1. ordered_waypoints is the most important field. If the intent is not clarification, provide an executable ordered waypoint sequence whenever possible.
2. For a single destination request, ordered_waypoints usually contains one place.
3. For theme, area, engineering, AI, robotics, student life, or first-visit requests, prefer tour or recommend_tour.
4. Use clarification only when you truly cannot map the request reliably.
5. Prefer knowledge-base ids in places, ordered_waypoints, and themes. If you are unsure, you may return a place name and the backend will normalize it.
6. reply_text must be 1-2 natural English sentences for an open-day guide. Do not include Chinese words, translations, or bilingual parentheses.
7. Do not output markdown and do not explain your reasoning."""


def run_nlu(user_message: str) -> NLUResult:
    """Parse user natural language into executable route/tour metadata."""

    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY is not configured; using fallback NLU")
        return _fallback_nlu(user_message)

    try:
        raw = _run_llm_parse(user_message)
        return _normalize_llm_output(raw, user_message)
    except Exception as e:
        logger.warning("OpenAI NLU unavailable; falling back to heuristics: %s", e)
        return _fallback_nlu(user_message)


def _run_llm_parse(user_message: str) -> _LLMGuideParse:
    """Call the model once, request JSON output, then validate with Pydantic locally."""

    client_kwargs = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        client_kwargs["base_url"] = settings.openai_base_url
    client = OpenAI(**client_kwargs)
    knowledge = list_place_summaries_for_prompt()
    user_prompt = (
        f"User input: {user_message}\n\n"
        "Return strict JSON with the following fields:\n"
        '{'
        '"intent":"route|tour|recommend_tour|clarification",'
        '"places":["..."],'
        '"ordered_waypoints":["..."],'
        '"themes":["..."],'
        '"reply_text":"...",'
        '"confidence":0.0,'
        '"needs_clarification":false,'
        '"clarification_question":null'
        '}'
    )
    completion = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _SYSTEM + "\n\nKnowledge base:\n" + knowledge},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    content = completion.choices[0].message.content or "{}"
    return _LLMGuideParse.model_validate_json(content)


def _normalize_place_tokens(tokens: list[str]) -> tuple[list[str], list[str]]:
    resolved: list[str] = []
    unresolved: list[str] = []
    for token in tokens:
        place_id = resolve_place_token(token)
        if place_id is None:
            unresolved.append(token)
        else:
            resolved.append(place_id)
    return _dedupe(resolved), unresolved


def _normalize_theme_tokens(tokens: list[str]) -> tuple[list[str], list[str]]:
    resolved: list[str] = []
    unresolved: list[str] = []
    for token in tokens:
        theme_id = resolve_theme_token(token)
        if theme_id is None:
            unresolved.append(token)
        else:
            resolved.append(theme_id)
    return _dedupe(resolved), unresolved


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _normalize_llm_output(raw: _LLMGuideParse, user_message: str) -> NLUResult:
    """Normalize LLM tokens to internal ids and enforce executable waypoint output."""

    places, unresolved_places = _normalize_place_tokens(raw.places)
    ordered_waypoints, unresolved_waypoints = _normalize_place_tokens(raw.ordered_waypoints)
    themes, unresolved_themes = _normalize_theme_tokens(raw.themes)

    intent = Intent(raw.intent)
    if intent == Intent.route and len(ordered_waypoints) > 1:
        intent = Intent.tour

    if not ordered_waypoints:
        if intent == Intent.route and places:
            ordered_waypoints = places[:1]
        elif intent in (Intent.tour, Intent.recommend_tour) and themes:
            ordered_waypoints = theme_waypoints_for_ids(themes)
        elif intent == Intent.tour and places:
            ordered_waypoints = places

    if intent == Intent.recommend_tour and not ordered_waypoints:
        if not themes:
            themes = [default_recommendation_theme()]
        ordered_waypoints = theme_waypoints_for_ids(themes) or default_recommendation_waypoints()

    unresolved = unresolved_places + unresolved_waypoints
    if unresolved and not ordered_waypoints:
        return _clarification_result(
            question=f"I cannot match '{unresolved[0]}' to a campus location yet. Could you use a more specific name?",
            user_message=user_message,
            confidence=raw.confidence,
            debug={
                "raw": raw.model_dump(),
                "unresolved_places": unresolved_places,
                "unresolved_waypoints": unresolved_waypoints,
                "unresolved_themes": unresolved_themes,
            },
        )

    if raw.needs_clarification or intent == Intent.clarification:
        question = _sanitize_english_text(
            raw.clarification_question
            or "Could you be more specific? For example, tell me a destination or the kind of route you want."
        )
        return _clarification_result(
            question=question,
            user_message=user_message,
            confidence=raw.confidence,
            debug={
                "raw": raw.model_dump(),
                "unresolved_places": unresolved_places,
                "unresolved_waypoints": unresolved_waypoints,
                "unresolved_themes": unresolved_themes,
            },
        )

    if not ordered_waypoints:
        return _clarification_result(
            question="I can guide you to a place, create a themed tour, or recommend a route. Try a destination, an interest, or ask me to recommend one.",
            user_message=user_message,
            confidence=raw.confidence,
            debug={"raw": raw.model_dump()},
        )

    reply_text = _sanitize_english_text(raw.reply_text) or _default_reply(intent, ordered_waypoints)
    return NLUResult(
        intent=intent,
        places=places,
        ordered_waypoints=ordered_waypoints,
        themes=themes,
        reply_text=reply_text,
        confidence=raw.confidence,
        needs_clarification=False,
        clarification_question=None,
        debug={
            "raw": raw.model_dump(),
            "unresolved_places": unresolved_places,
            "unresolved_waypoints": unresolved_waypoints,
            "unresolved_themes": unresolved_themes,
        },
    )


def _default_reply(intent: Intent, ordered_waypoints: list[str]) -> str:
    if intent == Intent.route and ordered_waypoints:
        return f"I found your destination and will now plan the route to {ordered_waypoints[0]}."
    if intent == Intent.tour:
        return "I will create a multi-stop route based on your interests and guide you through the relevant places in order."
    return "I will recommend a route that works well for the campus open day."


def _sanitize_english_text(text: str | None) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"[\u4e00-\u9fff]+", "", text)
    cleaned = re.sub(r"[（(]\s*[)）]", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    return cleaned.strip(" \n\t-")


def _clarification_result(
    question: str,
    user_message: str,
    confidence: float | None,
    debug: dict | None = None,
) -> NLUResult:
    merged_debug = {"user_message": user_message}
    if debug:
        merged_debug.update(debug)
    return NLUResult(
        intent=Intent.clarification,
        places=[],
        ordered_waypoints=[],
        themes=[],
        reply_text=question,
        confidence=confidence,
        needs_clarification=True,
        clarification_question=question,
        debug=merged_debug,
    )


def _fallback_nlu(message: str) -> NLUResult:
    """Fallback parser for local development when no API key is configured."""

    text = message.strip()
    place_ids = extract_place_mentions(text)
    theme_ids = extract_theme_mentions(text)
    lowered = text.lower()

    if any(token in text for token in ("推荐", "随便看看", "第一次来", "怎么逛", "值得看")) or any(
        token in lowered for token in ("recommend", "first visit", "what should i see", "worth seeing")
    ):
        theme_ids = theme_ids or [default_recommendation_theme()]
        waypoints = theme_waypoints_for_ids(theme_ids) or default_recommendation_waypoints()
        return NLUResult(
            intent=Intent.recommend_tour,
            places=[],
            ordered_waypoints=waypoints,
            themes=theme_ids,
            reply_text="I will recommend a route that works well for a quick open-day visit.",
            confidence=0.62,
            debug={"mode": "fallback"},
        )

    if len(place_ids) >= 2:
        return NLUResult(
            intent=Intent.tour,
            places=place_ids,
            ordered_waypoints=place_ids,
            themes=theme_ids,
            reply_text="I can see that you want to visit several places in sequence, so I will plan a multi-stop route.",
            confidence=0.68,
            debug={"mode": "fallback"},
        )

    if len(place_ids) == 1:
        return NLUResult(
            intent=Intent.route,
            places=place_ids,
            ordered_waypoints=place_ids,
            themes=[],
            reply_text="I found your destination. I will plan the route right away.",
            confidence=0.78,
            debug={"mode": "fallback"},
        )

    if theme_ids:
        return NLUResult(
            intent=Intent.tour,
            places=[],
            ordered_waypoints=theme_waypoints_for_ids(theme_ids),
            themes=theme_ids,
            reply_text="I understand the type of places you want to explore, and I will generate a themed campus tour.",
            confidence=0.66,
            debug={"mode": "fallback"},
        )

    return _clarification_result(
        question="Could you be a bit more specific? For example, you can ask for the library, PMB, AI, engineering, or student life.",
        user_message=text,
        confidence=0.3,
        debug={"mode": "fallback"},
    )
