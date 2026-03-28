from functools import lru_cache
from pathlib import Path

import yaml

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "campus.yaml"


@lru_cache
def load_campus() -> dict:
    with open(_DATA_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def list_place_summaries_for_prompt() -> str:
    data = load_campus()
    lines: list[str] = []
    for pid, p in data.get("places", {}).items():
        aliases = "、".join(p.get("aliases") or [])
        lines.append(f"- id={pid} name={p['name_zh']} aliases=[{aliases}]")
    for tid, t in data.get("themes", {}).items():
        aliases = "、".join(t.get("aliases") or [])
        lines.append(f"- theme_id={tid} name={t['name_zh']} aliases=[{aliases}]")
    return "\n".join(lines)
