import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getSession } from "./api";

export function MobilePage() {
  const { token } = useParams<{ token: string }>();
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    (async () => {
      try {
        const d = await getSession(token);
        if (!cancelled) setData(d);
      } catch (e: unknown) {
        if (!cancelled) setErr(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (err) {
    return (
      <div style={{ padding: 24 }}>
        <p>无法加载导览内容（可能已过期）。</p>
        <pre style={{ color: "#b91c1c", whiteSpace: "pre-wrap" }}>{err}</pre>
      </div>
    );
  }

  if (!data) {
    return <div style={{ padding: 24 }}>加载中…</div>;
  }

  const places = (data.places as { id: string; name_zh: string; blurb: string }[]) ?? [];

  return (
    <div style={{ padding: 24, maxWidth: 560, margin: "0 auto" }}>
      <h1 style={{ fontSize: "1.25rem" }}>导览摘要</h1>
      <p>{String(data.reply_zh ?? "")}</p>
      {data.route_summary_zh && <p style={{ color: "#555" }}>{String(data.route_summary_zh)}</p>}
      {places.length > 0 && (
        <ul>
          {places.map((p) => (
            <li key={p.id}>
              <strong>{p.name_zh}</strong> — {p.blurb}
            </li>
          ))}
        </ul>
      )}
      <p style={{ fontSize: "0.85rem", color: "#888" }}>
        机械臂动作：{String(data.arm_action ?? "")}
      </p>
    </div>
  );
}
