import json
import logging
import re

from openai import OpenAI

from app.config import settings
from app.models.schemas import Intent, NLUResult
from app.services.campus_data import list_place_summaries_for_prompt

logger = logging.getLogger(__name__)

_SYSTEM = """你是校园开放日导览装置的意图识别模块。只输出 JSON，不要 markdown。
根据用户中文输入判断意图并抽取槽位。

意图 intent 必须是以下之一：
- wayfinding：用户想去某个具体地点（问路）
- interest_tour：用户想按兴趣/主题参观（没有单一明确目的地）
- unclear：过于模糊、闲聊或与校园导览无关

规则：
- target_place_id / interest_theme_id 必须使用下面「知识库 id」，无法匹配时填 null。
- 若用户明确说出一个地点名，intent 一般为 wayfinding。
- 若用户表达「想了解理工区域」「AI 相关」等，intent 为 interest_tour。

知识库（id 必须从中选择）：
"""


def parse_nlu_json(text: str) -> NLUResult:
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}", text)
    raw = m.group(0) if m else text
    data = json.loads(raw)
    intent = Intent(data.get("intent", "unclear"))
    return NLUResult(
        intent=intent,
        target_place_id=data.get("target_place_id"),
        interest_theme_id=data.get("interest_theme_id"),
        confidence_note=data.get("confidence_note"),
    )


def run_nlu(user_message: str) -> NLUResult:
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY 未设置，使用启发式占位 NLU")
        return _fallback_nlu(user_message)

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        kb = list_place_summaries_for_prompt()
        user = f"用户说：{user_message}\n\n输出 JSON 格式：\n"
        user += '{"intent":"wayfinding|interest_tour|unclear","target_place_id":null,"interest_theme_id":null,"confidence_note":""}\n'
        user += "target_place_id 与 interest_theme_id 二选一或全 null。"

        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _SYSTEM + kb},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = completion.choices[0].message.content or "{}"
        try:
            return parse_nlu_json(content)
        except Exception as parse_err:
            logger.warning("NLU JSON 解析失败，回退到启发式：%s", parse_err)
            return _fallback_nlu(user_message)
    except Exception as e:
        logger.warning("OpenAI NLU 不可用，回退到启发式：%s", e)
        return _fallback_nlu(user_message)


def _fallback_nlu(message: str) -> NLUResult:
    m = message.strip()
    if any(k in m for k in ("图书馆", "图书")):
        return NLUResult(intent=Intent.wayfinding, target_place_id="library")
    if any(k in m for k in ("工程", "工院")):
        return NLUResult(intent=Intent.wayfinding, target_place_id="engineering")
    if "理工" in m or "工科" in m:
        return NLUResult(intent=Intent.interest_tour, interest_theme_id="stem")
    if any(k in m for k in ("机器人", "AI", "人工智能")):
        return NLUResult(intent=Intent.interest_tour, interest_theme_id="ai_robotics")
    return NLUResult(intent=Intent.unclear)
