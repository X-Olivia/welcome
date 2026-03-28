from __future__ import annotations

import logging
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


_SYSTEM = """你是校园开放日 AI 导览装置的自然语言理解模块。
你的任务不是生成长篇讲解，而是把用户输入解析成稳定、可执行的结构化导览计划。

你必须在以下意图中四选一：
- route：用户明确要去某一个地点
- tour：用户有主题/区域/多地点需求，需要规划一条经过多个地点的有序路线
- recommend_tour：用户表达模糊，但明显希望系统主动推荐一条可执行路线
- clarification：当前无法可靠映射到地点、主题或推荐路线，需要追问

输出规则：
1. ordered_waypoints 是最重要字段。只要 intent 不是 clarification，就尽量给出一条可执行的有序 waypoint 序列。
2. 如果用户只是问单地点，ordered_waypoints 通常只包含一个地点。
3. 如果用户在问主题、区域、工科、AI、机器人、校园生活、第一次来怎么逛等，应该优先输出 tour 或 recommend_tour。
4. 如果确实无法可靠判断，才输出 clarification，并给出 clarification_question。
5. places / ordered_waypoints / themes 优先使用知识库中的 id；如果你不确定 id，也可以先填你理解到的名称，后端会再标准化。
6. reply_text 只写 1-2 句自然说明，适合开放日导览场景。
7. 不要输出 markdown，不要解释推理过程。"""


def run_nlu(user_message: str) -> NLUResult:
    """Parse user natural language into executable route/tour metadata."""

    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY 未设置，使用启发式 fallback NLU")
        return _fallback_nlu(user_message)

    try:
        raw = _run_llm_parse(user_message)
        return _normalize_llm_output(raw, user_message)
    except Exception as e:
        logger.warning("OpenAI NLU 不可用，回退到启发式：%s", e)
        return _fallback_nlu(user_message)


def _run_llm_parse(user_message: str) -> _LLMGuideParse:
    """Call the model once, request JSON output, then validate with Pydantic locally."""

    client_kwargs = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        client_kwargs["base_url"] = settings.openai_base_url
    client = OpenAI(**client_kwargs)
    knowledge = list_place_summaries_for_prompt()
    user_prompt = (
        f"用户输入：{user_message}\n\n"
        "请严格输出 JSON，对应字段如下：\n"
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
            {"role": "system", "content": _SYSTEM + "\n\n知识库：\n" + knowledge},
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
            question=f"我还不能确定「{unresolved[0]}」对应校园里的哪个地点。可以换一个更具体的名称吗？",
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
        question = raw.clarification_question or "可以说得更具体一点吗？例如你想去哪个地点，或者想了解哪一类路线。"
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
            question="我可以帮你指路、规划主题导览或推荐路线。可以说一个地点、一个兴趣主题，或让我直接推荐一条路线。",
            user_message=user_message,
            confidence=raw.confidence,
            debug={"raw": raw.model_dump()},
        )

    reply_text = raw.reply_text.strip() or _default_reply(intent, ordered_waypoints)
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
        return f"我已经为你识别到目标地点，接下来会规划前往 {ordered_waypoints[0]} 的路线。"
    if intent == Intent.tour:
        return "我会根据你的兴趣生成一条多点导览路线，并按顺序带你经过相关地点。"
    return "我会为你推荐一条适合开放日现场体验的校园路线。"


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

    if any(token in text for token in ("推荐", "随便看看", "第一次来", "怎么逛", "值得看")) or "recommend" in lowered:
        theme_ids = theme_ids or [default_recommendation_theme()]
        waypoints = theme_waypoints_for_ids(theme_ids) or default_recommendation_waypoints()
        return NLUResult(
            intent=Intent.recommend_tour,
            places=[],
            ordered_waypoints=waypoints,
            themes=theme_ids,
            reply_text="我先为你推荐一条适合开放日快速体验的校园路线。",
            confidence=0.62,
            debug={"mode": "fallback"},
        )

    if len(place_ids) >= 2:
        return NLUResult(
            intent=Intent.tour,
            places=place_ids,
            ordered_waypoints=place_ids,
            themes=theme_ids,
            reply_text="我识别到你想依次经过多个地点，接下来会为你规划一条多点导览路线。",
            confidence=0.68,
            debug={"mode": "fallback"},
        )

    if len(place_ids) == 1:
        return NLUResult(
            intent=Intent.route,
            places=place_ids,
            ordered_waypoints=place_ids,
            themes=[],
            reply_text="我识别到你的目标地点了，马上为你规划路线。",
            confidence=0.78,
            debug={"mode": "fallback"},
        )

    if theme_ids:
        return NLUResult(
            intent=Intent.tour,
            places=[],
            ordered_waypoints=theme_waypoints_for_ids(theme_ids),
            themes=theme_ids,
            reply_text="我识别到你的兴趣方向了，接下来会生成一条主题导览路线。",
            confidence=0.66,
            debug={"mode": "fallback"},
        )

    return _clarification_result(
        question="可以说得更具体一点吗？例如你想去图书馆、PMB，或者想了解 AI、理工区域、校园生活。",
        user_message=text,
        confidence=0.3,
        debug={"mode": "fallback"},
    )
