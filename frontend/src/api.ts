export type ArmAction =
  | "point_left"
  | "point_right"
  | "point_forward"
  | "wave"
  | "idle";

export type Intent = "route" | "tour" | "recommend_tour" | "clarification";

export interface PlaceCard {
  id: string;
  name_zh: string;
  blurb: string;
  x?: number | null;
  y?: number | null;
}

export interface MapPoint {
  x: number;
  y: number;
}

export interface GuideSession {
  intent: Intent;
  reply_zh: string;
  arm_action: ArmAction;
  places: PlaceCard[];
  route_summary_zh: string | null;
  route_polyline: MapPoint[];
  route_distance_px: number | null;
}

export interface GuideResponse extends GuideSession {
  mobile_url: string | null;
  qr_data_url: string | null;
  debug?: Record<string, unknown>;
}

export interface RoutePlanResponse {
  mode: Intent;
  summary: string;
  arm_action: ArmAction;
  waypoints: PlaceCard[];
  path: MapPoint[];
  route_distance_px: number | null;
  share_url: string | null;
}

export interface VoiceTranscriptResponse {
  text: string;
  duration_ms?: number | null;
}

function apiBase(): string {
  return import.meta.env.VITE_API_BASE?.replace(/\/$/, "") ?? "";
}

async function parseApiError(response: Response): Promise<string> {
  const text = await response.text();
  let messageText = text || response.statusText;

  try {
    const json = JSON.parse(text) as { detail?: unknown };
    if (typeof json.detail === "string") messageText = json.detail;
    else if (Array.isArray(json.detail)) {
      messageText = json.detail
        .map((item: { msg?: string }) => item.msg ?? String(item))
        .join("; ");
    }
  } catch {
    // Preserve text body when it is not JSON.
  }

  if (response.status >= 500) {
    const shortMessage =
      /internal server error/i.test(messageText) || messageText.length < 5
        ? "server processing failed"
        : messageText.slice(0, 120);
    messageText = `The service is temporarily unavailable (${shortMessage}). Check whether the backend is running and the dependencies are installed.`;
  }
  return messageText;
}

export async function postGuide(message: string): Promise<GuideResponse> {
  const response = await fetch(`${apiBase()}/api/guide`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) throw new Error(await parseApiError(response));

  return (await response.json()) as GuideResponse;
}

export async function getSession(token: string): Promise<GuideSession> {
  const response = await fetch(`${apiBase()}/api/session/${encodeURIComponent(token)}`);
  if (!response.ok) throw new Error(await response.text());
  return (await response.json()) as GuideSession;
}

export async function postRoute(destination: string): Promise<RoutePlanResponse> {
  const response = await fetch(`${apiBase()}/api/route`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ destination }),
  });
  if (!response.ok) throw new Error(await response.text());
  return (await response.json()) as RoutePlanResponse;
}

export async function postMultiRoute(
  waypoints: string[],
  mode: Intent = "tour",
): Promise<RoutePlanResponse> {
  const response = await fetch(`${apiBase()}/api/route/multi`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ waypoints, mode }),
  });
  if (!response.ok) throw new Error(await response.text());
  return (await response.json()) as RoutePlanResponse;
}

export async function postVoiceTranscribe(
  audio: Blob,
  options?: { language?: string },
): Promise<VoiceTranscriptResponse> {
  const formData = new FormData();
  formData.append("audio", audio, "voice-input.webm");
  if (options?.language) formData.append("language", options.language);

  const response = await fetch(`${apiBase()}/api/voice/transcribe`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) throw new Error(await parseApiError(response));
  return (await response.json()) as VoiceTranscriptResponse;
}

export async function fetchSpeechAudio(
  text: string,
  options?: { language?: string; speed?: number },
): Promise<Blob> {
  const response = await fetch(`${apiBase()}/api/voice/speak`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      language: options?.language ?? "en",
      speed: options?.speed,
    }),
  });
  if (!response.ok) throw new Error(await parseApiError(response));
  return await response.blob();
}
