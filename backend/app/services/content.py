from app.models.schemas import ArmAction, Intent, NLUResult, PlaceCard
from app.services.campus_data import load_campus


def direction_to_arm(direction: str) -> ArmAction:
    d = (direction or "forward").lower()
    if d in ("left", "l"):
        return ArmAction.point_left
    if d in ("right", "r"):
        return ArmAction.point_right
    return ArmAction.point_forward


def build_wayfinding(place_id: str) -> tuple[list[PlaceCard], str, ArmAction]:
    data = load_campus()
    places = data.get("places", {})
    if place_id not in places:
        return [], "抱歉，我暂时还不知道这个地点在哪里。", ArmAction.idle
    p = places[place_id]
    card = PlaceCard(id=place_id, name_zh=p["name_zh"], blurb=p["blurb"])
    arm = direction_to_arm(p.get("direction", "forward"))
    summary = f"「{p['name_zh']}」：{p['blurb']}"
    return [card], summary, arm


def build_interest_tour(theme_id: str) -> tuple[list[PlaceCard], str, ArmAction]:
    data = load_campus()
    themes = data.get("themes", {})
    if theme_id not in themes:
        return [], "暂时没有匹配的主题导览，可以试试说「图书馆怎么走」。", ArmAction.idle
    t = themes[theme_id]
    place_ids: list[str] = list(t.get("place_ids") or [])
    places_data = data.get("places", {})
    cards: list[PlaceCard] = []
    for pid in place_ids:
        if pid in places_data:
            q = places_data[pid]
            cards.append(PlaceCard(id=pid, name_zh=q["name_zh"], blurb=q["blurb"]))
    if not cards:
        return [], "主题数据不完整。", ArmAction.idle
    first = places_data.get(place_ids[0], {})
    arm = direction_to_arm(first.get("direction", "forward"))
    intro = t.get("intro_zh", "")
    summary = intro + " 建议第一站：" + cards[0].name_zh + "。"
    return cards, summary, arm


def compose_reply(nlu: NLUResult) -> tuple[list[PlaceCard], str | None, ArmAction, Intent]:
    if nlu.intent == Intent.wayfinding and nlu.target_place_id:
        cards, summary, arm = build_wayfinding(nlu.target_place_id)
        return cards, summary, arm, nlu.intent
    if nlu.intent == Intent.interest_tour and nlu.interest_theme_id:
        cards, summary, arm = build_interest_tour(nlu.interest_theme_id)
        return cards, summary, arm, nlu.intent
    if nlu.intent == Intent.wayfinding:
        return [], "可以说得更具体一点吗？例如「图书馆怎么走」。", ArmAction.wave, Intent.unclear
    if nlu.intent == Intent.interest_tour:
        return (
            [],
            "可以说说你感兴趣的方向吗？例如「理工区域」或「机器人和 AI」。",
            ArmAction.wave,
            Intent.unclear,
        )
    return [], "我主要能帮你指路或推荐参观主题，试试问「食堂在哪」或「想了解理工区域」。", ArmAction.idle, Intent.unclear
