import { useState } from "react";
import type { GuideResponse } from "./api";
import { postGuide } from "./api";

export function App() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<GuideResponse | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = input.trim();
    if (!q) return;
    setLoading(true);
    setErr(null);
    try {
      const data = await postGuide(q);
      setResult(data);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={shell}>
      <div style={inner}>
        <header style={header}>
          <p style={eyebrow}>校园开放日</p>
          <h1 style={title}>AI 导览终端</h1>
          <p style={subtitle}>
            问路或描述兴趣，大屏展示结果；机械臂执行指向（当前可为 mock）。
          </p>
        </header>

        <main style={main}>
          <form onSubmit={onSubmit} style={form}>
            <label style={label}>你想去哪里 / 想了解什么？</label>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              rows={4}
              placeholder="例如：图书馆怎么走？ / 我想了解理工区域"
              style={textarea}
              disabled={loading}
            />
            <button type="submit" disabled={loading} style={btn}>
              {loading ? "分析中…" : "发送"}
            </button>
          </form>

          {err && (
            <div style={errorBox} role="alert">
              {err}
            </div>
          )}

          {result && (
            <section style={resultBox} aria-live="polite">
              <h2 style={resultTitle}>导览结果</h2>
              <p style={reply}>{result.reply_zh}</p>

              {result.route_summary_zh && result.route_summary_zh !== result.reply_zh && (
                <p style={routeExtra}>{result.route_summary_zh}</p>
              )}

              <div style={meta}>
                <span style={metaPill}>意图：{intentLabel(result.intent)}</span>
                <span style={metaPill}>机械臂：{armLabel(result.arm_action)}</span>
              </div>

              {result.places.length > 0 && (
                <ul style={placeList}>
                  {result.places.map((p) => (
                    <li key={p.id} style={placeItem}>
                      <strong>{p.name_zh}</strong>
                      <span style={placeBlurb}> — {p.blurb}</span>
                    </li>
                  ))}
                </ul>
              )}

              {result.qr_data_url && (
                <div style={qrBlock}>
                  <p style={qrHint}>手机扫码继续查看</p>
                  <img src={result.qr_data_url} alt="二维码" width={180} height={180} style={qrImg} />
                  {result.mobile_url && (
                    <p style={mobileUrl}>{result.mobile_url}</p>
                  )}
                </div>
              )}
              {!result.qr_data_url && result.mobile_url && (
                <p style={qrFallback}>扫码图未生成时，可在手机浏览器打开：{result.mobile_url}</p>
              )}
            </section>
          )}
        </main>
      </div>
    </div>
  );
}

function intentLabel(i: GuideResponse["intent"]): string {
  const m: Record<string, string> = {
    wayfinding: "问路",
    interest_tour: "主题参观",
    unclear: "待澄清",
  };
  return m[i] ?? i;
}

function armLabel(a: GuideResponse["arm_action"]): string {
  const m: Record<string, string> = {
    point_left: "指向左侧",
    point_right: "指向右侧",
    point_forward: "指向前方",
    wave: "挥手",
    idle: "待机",
  };
  return m[a] ?? a;
}

const shell: React.CSSProperties = {
  minHeight: "100vh",
  background: "linear-gradient(165deg, #e8eef9 0%, #f4f6fb 45%, #eef2ff 100%)",
  padding: "clamp(1.25rem, 3vw, 2.5rem)",
};

const inner: React.CSSProperties = {
  maxWidth: 960,
  margin: "0 auto",
};

const header: React.CSSProperties = {
  marginBottom: "clamp(1.25rem, 3vw, 2rem)",
  textAlign: "center",
};

const eyebrow: React.CSSProperties = {
  margin: 0,
  fontSize: "0.85rem",
  fontWeight: 600,
  letterSpacing: "0.12em",
  textTransform: "uppercase",
  color: "#64748b",
};

const title: React.CSSProperties = {
  margin: "0.35rem 0 0",
  fontSize: "clamp(1.75rem, 4vw, 2.35rem)",
  fontWeight: 700,
  color: "#0f172a",
  letterSpacing: "-0.02em",
};

const subtitle: React.CSSProperties = {
  margin: "0.65rem 0 0",
  fontSize: "clamp(0.95rem, 2vw, 1.05rem)",
  color: "#475569",
  lineHeight: 1.55,
  maxWidth: 520,
  marginLeft: "auto",
  marginRight: "auto",
};

const main: React.CSSProperties = {};

const form: React.CSSProperties = {
  background: "#fff",
  borderRadius: 16,
  padding: "clamp(1.25rem, 3vw, 1.75rem)",
  boxShadow: "0 12px 40px rgba(15, 23, 42, 0.08)",
  border: "1px solid rgba(148, 163, 184, 0.25)",
};

const label: React.CSSProperties = {
  display: "block",
  fontWeight: 650,
  marginBottom: 10,
  fontSize: "1.05rem",
  color: "#1e293b",
};

const textarea: React.CSSProperties = {
  width: "100%",
  padding: "0.9rem 1rem",
  borderRadius: 12,
  border: "1px solid #cbd5e1",
  font: "inherit",
  fontSize: "1.05rem",
  lineHeight: 1.5,
  resize: "vertical",
  minHeight: "5.5rem",
};

const btn: React.CSSProperties = {
  marginTop: 14,
  padding: "0.7rem 1.5rem",
  borderRadius: 10,
  border: "none",
  background: "linear-gradient(180deg, #3b82f6 0%, #2563eb 100%)",
  color: "#fff",
  fontWeight: 650,
  fontSize: "1.02rem",
  cursor: "pointer",
  boxShadow: "0 4px 14px rgba(37, 99, 235, 0.35)",
};

const errorBox: React.CSSProperties = {
  marginTop: 18,
  padding: "0.85rem 1.1rem",
  background: "#fef2f2",
  color: "#b91c1c",
  borderRadius: 12,
  border: "1px solid #fecaca",
  fontSize: "0.95rem",
  lineHeight: 1.5,
};

const resultBox: React.CSSProperties = {
  marginTop: 28,
  background: "#fff",
  borderRadius: 16,
  padding: "clamp(1.25rem, 3vw, 1.75rem)",
  boxShadow: "0 12px 40px rgba(15, 23, 42, 0.08)",
  border: "1px solid rgba(148, 163, 184, 0.2)",
};

const resultTitle: React.CSSProperties = {
  marginTop: 0,
  marginBottom: 12,
  fontSize: "1.15rem",
  color: "#334155",
  fontWeight: 650,
};

const reply: React.CSSProperties = {
  fontSize: "clamp(1.1rem, 2.5vw, 1.35rem)",
  lineHeight: 1.65,
  color: "#0f172a",
  margin: 0,
};

const routeExtra: React.CSSProperties = {
  marginTop: 12,
  fontSize: "1rem",
  color: "#475569",
  lineHeight: 1.55,
};

const meta: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: 8,
  marginTop: 16,
};

const metaPill: React.CSSProperties = {
  fontSize: "0.88rem",
  color: "#475569",
  background: "#f1f5f9",
  padding: "6px 12px",
  borderRadius: 999,
};

const placeList: React.CSSProperties = {
  paddingLeft: "1.25rem",
  margin: "16px 0 0",
};

const placeItem: React.CSSProperties = {
  marginBottom: 10,
  fontSize: "1rem",
  lineHeight: 1.5,
  color: "#334155",
};

const placeBlurb: React.CSSProperties = {
  fontWeight: 400,
};

const qrBlock: React.CSSProperties = {
  marginTop: 20,
  paddingTop: 20,
  borderTop: "1px solid #e2e8f0",
};

const qrHint: React.CSSProperties = {
  fontSize: "0.92rem",
  color: "#64748b",
  margin: "0 0 10px",
};

const qrImg: React.CSSProperties = {
  borderRadius: 8,
  border: "1px solid #e2e8f0",
};

const mobileUrl: React.CSSProperties = {
  wordBreak: "break-all",
  fontSize: "0.82rem",
  color: "#64748b",
  marginTop: 8,
};

const qrFallback: React.CSSProperties = {
  marginTop: 16,
  fontSize: "0.88rem",
  color: "#64748b",
  wordBreak: "break-all",
  lineHeight: 1.5,
};
