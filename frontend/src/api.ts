export type ArmAction =
  | "point_left"
  | "point_right"
  | "point_forward"
  | "wave"
  | "idle";

export type Intent = "wayfinding" | "interest_tour" | "unclear";

export interface PlaceCard {
  id: string;
  name_zh: string;
  blurb: string;
}

export interface GuideResponse {
  intent: Intent;
  reply_zh: string;
  arm_action: ArmAction;
  places: PlaceCard[];
  route_summary_zh: string | null;
  mobile_url: string | null;
  qr_data_url: string | null;
  debug?: Record<string, unknown>;
}

function apiBase(): string {
  return import.meta.env.VITE_API_BASE?.replace(/\/$/, "") ?? "";
}

export async function postGuide(message: string): Promise<GuideResponse> {
  const r = await fetch(`${apiBase()}/api/guide`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!r.ok) {
    const t = await r.text();
    let msg = t || r.statusText;
    try {
      const j = JSON.parse(t) as { detail?: unknown };
      if (typeof j.detail === "string") msg = j.detail;
      else if (Array.isArray(j.detail))
        msg = j.detail.map((x: { msg?: string }) => x.msg ?? String(x)).join("；");
    } catch {
      /* keep text */
    }
    if (r.status >= 500) {
      const short =
        /internal server error/i.test(msg) || msg.length < 5
          ? "后端处理出错"
          : msg.slice(0, 120);
      msg = `服务暂时不可用（${short}）。可检查后端是否已启动、依赖是否已安装。`;
    }
    throw new Error(msg);
  }
  return r.json() as Promise<GuideResponse>;
}

export async function getSession(token: string): Promise<Record<string, unknown>> {
  const r = await fetch(`${apiBase()}/api/session/${encodeURIComponent(token)}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<Record<string, unknown>>;
}
