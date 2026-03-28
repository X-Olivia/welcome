from app.models.schemas import ArmAction, Intent, NLUResult, PlaceCard
from app.services.campus_data import build_place_cards, place_direction, theme_intro


def direction_to_arm(direction: str) -> ArmAction:
    d = (direction or "forward").lower()
    if d in ("left", "l"):
        return ArmAction.point_left
    if d in ("right", "r"):
        return ArmAction.point_right
    return ArmAction.point_forward


def arm_action_for_places(place_ids: list[str]) -> ArmAction:
    if not place_ids:
        return ArmAction.idle
    return direction_to_arm(place_direction(place_ids[0]))


def _fallback_reply(nlu: NLUResult, cards: list[PlaceCard]) -> str:
    if nlu.intent == Intent.route and cards:
        return f"已为你识别到目标地点「{cards[0].name_zh}」，接下来会规划从导览装置到该地点的路线。"
    if nlu.intent in (Intent.tour, Intent.recommend_tour) and cards:
        theme_intro_text = theme_intro(nlu.themes[0]) if nlu.themes else None
        if theme_intro_text:
            return theme_intro_text + f" 建议第一站：{cards[0].name_zh}。"
        return f"我为你整理了一条包含 {len(cards)} 个停靠点的导览路线，建议第一站先去 {cards[0].name_zh}。"
    return "我可以继续帮你规划路线。"


def compose_reply(nlu: NLUResult) -> tuple[list[PlaceCard], str | None, ArmAction, Intent]:
    if nlu.intent == Intent.clarification or nlu.needs_clarification:
        text = nlu.clarification_question or nlu.reply_text or "可以再说得具体一点吗？"
        return [], text, ArmAction.wave, Intent.clarification

    cards = build_place_cards(nlu.ordered_waypoints)
    if not cards:
        return [], "我还没有找到可以执行的导览目标，可以换一种说法再试一次。", ArmAction.wave, Intent.clarification

    arm = arm_action_for_places(nlu.ordered_waypoints)
    summary = nlu.reply_text.strip() or _fallback_reply(nlu, cards)
    return cards, summary, arm, nlu.intent


def compose_route_plan(
    waypoint_ids: list[str],
    intent: Intent,
    reply_text: str | None = None,
) -> tuple[list[PlaceCard], str, ArmAction]:
    """Convert waypoint ids into route cards and a user-facing summary."""

    cards = build_place_cards(waypoint_ids)
    if not cards:
        return [], "我还没有找到可以执行的导览目标。", ArmAction.wave

    nlu = NLUResult(
        intent=intent,
        ordered_waypoints=[card.id for card in cards],
        reply_text=reply_text or "",
    )
    summary = reply_text.strip() if reply_text else _fallback_reply(nlu, cards)
    return cards, summary, arm_action_for_places([card.id for card in cards])
