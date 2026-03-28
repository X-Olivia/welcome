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
        return f"I found your destination, {cards[0].name_zh}. I will now plan the route from the guide station."
    if nlu.intent in (Intent.tour, Intent.recommend_tour) and cards:
        theme_intro_text = theme_intro(nlu.themes[0]) if nlu.themes else None
        if theme_intro_text:
            return theme_intro_text + f" Suggested first stop: {cards[0].name_zh}."
        return f"I have prepared a tour with {len(cards)} stops. A good first stop is {cards[0].name_zh}."
    return "I can continue planning a route for you."


def compose_reply(nlu: NLUResult) -> tuple[list[PlaceCard], str | None, ArmAction, Intent]:
    if nlu.intent == Intent.clarification or nlu.needs_clarification:
        text = nlu.clarification_question or nlu.reply_text or "Could you be a bit more specific?"
        return [], text, ArmAction.wave, Intent.clarification

    cards = build_place_cards(nlu.ordered_waypoints)
    if not cards:
        return [], "I could not find a routeable destination yet. Please try another description.", ArmAction.wave, Intent.clarification

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
        return [], "I could not find a routeable destination.", ArmAction.wave

    nlu = NLUResult(
        intent=intent,
        ordered_waypoints=[card.id for card in cards],
        reply_text=reply_text or "",
    )
    summary = reply_text.strip() if reply_text else _fallback_reply(nlu, cards)
    return cards, summary, arm_action_for_places([card.id for card in cards])
