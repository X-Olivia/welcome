import io
import logging

from app.config import settings
from app.models.schemas import GuideResponse, Intent, NLUResult
from app.services.content import compose_reply
from app.services.nlu import run_nlu
from app.services.session_store import put as session_put

logger = logging.getLogger(__name__)


def _qr_data_url(url: str) -> str | None:
    try:
        import base64

        import qrcode
    except ImportError:
        logger.warning("未安装 qrcode，跳过二维码。请执行: pip install 'qrcode[pil]'")
        return None
    try:
        buf = io.BytesIO()
        img = qrcode.make(url)
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        logger.warning("二维码生成失败：%s", e)
        return None


def run_guide_pipeline(message: str) -> GuideResponse:
    nlu: NLUResult = run_nlu(message)
    places, route_summary, arm_action, effective_intent = compose_reply(nlu)

    if route_summary:
        reply_zh = route_summary
    else:
        reply_zh = "好的。"

    session_payload = {
        "reply_zh": reply_zh,
        "intent": effective_intent.value,
        "places": [p.model_dump() for p in places],
        "route_summary_zh": route_summary,
        "arm_action": arm_action.value,
    }
    token = session_put(session_payload)
    mobile_url = f"{settings.public_base_url.rstrip('/')}/m/{token}"
    qr_data_url = _qr_data_url(mobile_url)

    return GuideResponse(
        intent=effective_intent,
        reply_zh=reply_zh,
        arm_action=arm_action,
        places=places,
        route_summary_zh=route_summary,
        mobile_url=mobile_url,
        qr_data_url=qr_data_url,
        debug={
            "nlu": nlu.model_dump(),
            "session_token": token,
        },
    )
