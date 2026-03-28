import { FormEvent, useMemo, useState } from "react";
import { GuideMap } from "./GuideMap";
import { type GuideResponse, postGuide } from "./api";
import { getPoiByPlaceId, getRouteMetrics, polylineDistance } from "./campusMap";

const starterPrompts = [
  "图书馆怎么走？",
  "我想看看 AI 和机器人相关区域",
  "带家长快速逛一下理工区域",
  "想了解校园生活和吃饭的地方",
];

export function App() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GuideResponse | null>(null);
  const [qrVisible, setQrVisible] = useState(false);

  const routeDistance = useMemo(
    () => result?.route_distance_px ?? polylineDistance(result?.route_polyline ?? []),
    [result],
  );
  const metrics = useMemo(() => getRouteMetrics(routeDistance), [routeDistance]);

  async function runQuery(message: string) {
    const text = message.trim();
    if (!text) return;

    setLoading(true);
    setError(null);
    setQrVisible(false);
    try {
      const data = await postGuide(text);
      setResult(data);
      setInput(text);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runQuery(input);
  }

  const topStop = result?.places[0];
  const topStopMeta = topStop ? getPoiByPlaceId(topStop.id) : null;
  const stopCount = result?.places.length ?? 0;
  const showTransfer = Boolean(result?.mobile_url && stopCount > 0);
  const overviewText =
    result?.route_summary_zh?.trim() || result?.reply_zh?.trim() || "Tell the guide what you want to explore.";

  return (
    <div className="app-shell">
      <div className="app-shell__glow app-shell__glow--left" />
      <div className="app-shell__glow app-shell__glow--right" />

      <header className="topbar">
        <div>
          <p className="eyebrow">UNNC Open Day</p>
          <h1 className="hero-title">Ask, Discover, Start Your Route</h1>
          <p className="hero-copy">
            A campus guide experience designed for open-day visitors. Ask for a place, a theme,
            or the kind of campus life you want to explore.
          </p>
        </div>

        <div className="topbar__meta">
          <span className="meta-chip">AI Guide</span>
          <span className="meta-chip">Live Map</span>
          <span className="meta-chip">Phone Handoff</span>
        </div>
      </header>

      <main className="desktop-grid">
        <section className="panel panel--prompt">
          <div className="panel__header">
            <p className="panel__eyebrow">Main Interaction</p>
            <h2 className="panel__title">Tell the guide what you want to see</h2>
            <p className="panel__copy">
              Use the keyboard or natural language to describe a destination, a theme, or a short
              campus visit you care about.
            </p>
          </div>

          <form className="prompt-form" onSubmit={onSubmit}>
            <label className="prompt-form__label" htmlFor="guide-input">
              Where would you like to go, or what would you like to explore today?
            </label>
            <textarea
              id="guide-input"
              className="prompt-form__textarea"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              rows={4}
              placeholder="For example: 图书馆怎么走？ / 我想看 AI 和机器人 / 带家长逛一下校园生活"
              disabled={loading}
            />
            <div className="prompt-form__actions">
              <button className="primary-button" type="submit" disabled={loading || !input.trim()}>
                {loading ? "Planning Route..." : "Generate Route"}
              </button>
              <p className="micro-note">
                You can ask for places, themes, or an open-day route tailored to your interests.
              </p>
            </div>
          </form>

          <div className="suggestion-row" aria-label="Suggested prompts">
            {starterPrompts.map((prompt) => (
              <button
                key={prompt}
                className="suggestion-chip"
                type="button"
                onClick={() => {
                  setInput(prompt);
                  void runQuery(prompt);
                }}
                disabled={loading}
              >
                {prompt}
              </button>
            ))}
          </div>

          <section className="panel panel--result">
            <div className="result-header">
              <div>
                <p className="panel__eyebrow">Guide Result</p>
                <h3 className="result-title">
                  {loading
                    ? "Understanding your request"
                    : result
                      ? "Your Open Day Route"
                      : "Ready to shape a campus route"}
                </h3>
              </div>
              {result && (
                <span className={`intent-pill intent-pill--${result.intent}`}>
                  {intentLabel(result.intent)}
                </span>
              )}
            </div>

            {loading && (
              <div className="loading-state" aria-live="polite">
                <div className="loading-line loading-line--wide" />
                <div className="loading-line" />
                <div className="loading-line loading-line--short" />
                <div className="loading-card-row">
                  <div className="loading-card" />
                  <div className="loading-card" />
                  <div className="loading-card" />
                </div>
              </div>
            )}

            {!loading && !result && !error && (
              <div className="empty-state">
                <p className="empty-state__lead">
                  The map will stay visible while the guide prepares a route for you.
                </p>
                <div className="feature-grid">
                  <article className="feature-card">
                    <h4>Ask naturally</h4>
                    <p>Type a place, a topic, or the kind of experience you want on open day.</p>
                  </article>
                  <article className="feature-card">
                    <h4>See the route</h4>
                    <p>The recommended path, key stops, and next move will appear on the map.</p>
                  </article>
                  <article className="feature-card">
                    <h4>Continue on phone</h4>
                    <p>Scan a QR code only when you want to take the route with you.</p>
                  </article>
                </div>
              </div>
            )}

            {!loading && error && (
              <div className="message-card message-card--error" role="alert">
                <h4>Route unavailable right now</h4>
                <p>{error}</p>
              </div>
            )}

            {!loading && result && (
              <div className="result-body">
                <p className="overview-text">{overviewText}</p>

                {stopCount > 0 ? (
                  <>
                    <div className="metric-row">
                      <div className="metric-card">
                        <span className="metric-card__label">Estimated Walk</span>
                        <strong>{metrics.minutes} min</strong>
                      </div>
                      <div className="metric-card">
                        <span className="metric-card__label">Recommended Stops</span>
                        <strong>{stopCount}</strong>
                      </div>
                      <div className="metric-card">
                        <span className="metric-card__label">Best For</span>
                        <strong>{audienceLabel(result.intent)}</strong>
                      </div>
                    </div>

                    <div className="next-step-card">
                      <p className="next-step-card__eyebrow">Next Step</p>
                      <h4>
                        Head toward {topStop?.name_zh}
                        {topStopMeta ? ` · ${topStopMeta.area}` : ""}
                      </h4>
                      <p>
                        Start from the guide station and follow the highlighted line. The first stop
                        sets the tone for this route and keeps the walk easy to follow.
                      </p>
                    </div>

                    <div className="stop-list">
                      {result.places.map((stop, index) => {
                        const meta = getPoiByPlaceId(stop.id);
                        return (
                          <article className="stop-card" key={stop.id}>
                            <div className="stop-card__index">{index + 1}</div>
                            <div>
                              <div className="stop-card__title-row">
                                <h4>{stop.name_zh}</h4>
                                {meta && <span>{meta.area}</span>}
                              </div>
                              <p>{stop.blurb}</p>
                              {meta && <p className="stop-card__relation">{meta.relation}</p>}
                            </div>
                          </article>
                        );
                      })}
                    </div>
                  </>
                ) : (
                  <div className="message-card message-card--soft">
                    <h4>Let’s narrow it down</h4>
                    <p>
                      Try naming a destination, a subject area, or the kind of campus experience
                      you want to see. The guide can then generate a clearer route.
                    </p>
                    <div className="clarify-row">
                      {starterPrompts.slice(0, 3).map((prompt) => (
                        <button
                          key={prompt}
                          className="suggestion-chip suggestion-chip--soft"
                          type="button"
                          onClick={() => {
                            setInput(prompt);
                            void runQuery(prompt);
                          }}
                        >
                          {prompt}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </section>

          {showTransfer && (
            <section className="panel panel--transfer">
              {!qrVisible ? (
                <div className="transfer-cta">
                  <div>
                    <p className="panel__eyebrow">Continue On Mobile</p>
                    <h3>Take this route on your phone</h3>
                    <p>
                      Generate a QR code when you want to carry the route, stop list, and map view
                      with you.
                    </p>
                  </div>
                  <button className="primary-button" type="button" onClick={() => setQrVisible(true)}>
                    Take This Route on Your Phone
                  </button>
                </div>
              ) : (
                <div className="qr-panel">
                  <div>
                    <p className="panel__eyebrow">QR Ready</p>
                    <h3>Scan to continue on your phone</h3>
                    <p>Take this route with you and explore campus at your own pace.</p>
                    {result?.mobile_url && (
                      <p className="micro-note micro-note--inline">{result.mobile_url}</p>
                    )}
                  </div>
                  {result?.qr_data_url ? (
                    <div className="qr-box">
                      <img src={result.qr_data_url} alt="Route QR code" className="qr-box__image" />
                    </div>
                  ) : (
                    <div className="message-card message-card--soft">
                      <h4>QR image not available</h4>
                      <p>The mobile link is still ready. Open it directly if needed.</p>
                    </div>
                  )}
                </div>
              )}
            </section>
          )}
        </section>

        <section className="panel panel--map">
          <div className="map-panel__header">
            <div>
              <p className="panel__eyebrow">Live Campus Map</p>
              <h2 className="panel__title">Map first, route second, details alongside</h2>
            </div>
            <div className="map-legend">
              <span>
                <i className="legend-swatch legend-swatch--station" />
                Guide Station
              </span>
              <span>
                <i className="legend-swatch legend-swatch--route" />
                Suggested Route
              </span>
              <span>
                <i className="legend-swatch legend-swatch--stop" />
                Key Stops
              </span>
            </div>
          </div>

          <GuideMap
            places={result?.places ?? []}
            routePolyline={result?.route_polyline ?? []}
            mode={loading ? "loading" : result ? "result" : "initial"}
          />

          <div className="map-panel__footer">
            <div>
              <p className="map-panel__footer-label">Route Summary</p>
              <p>{stopCount > 0 ? overviewText : "The route will appear here after a request."}</p>
            </div>
            <div>
              <p className="map-panel__footer-label">Current Focus</p>
              <p>
                {stopCount > 0
                  ? `${stopCount} stops · starting with ${result?.places[0].name_zh}`
                  : "Open Day campus overview"}
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="page-footer">
        <span>Discover</span>
        <span>Route</span>
        <span>Open Day</span>
        <span>AI Guide</span>
        <span>University of Nottingham Ningbo China</span>
      </footer>
    </div>
  );
}

function audienceLabel(intent: GuideResponse["intent"]): string {
  if (intent === "route") return "Quick visitors";
  if (intent === "tour") return "Topic explorers";
  if (intent === "recommend_tour") return "First-time visitors";
  return "Need more detail";
}

function intentLabel(intent: GuideResponse["intent"]): string {
  if (intent === "route") return "Route";
  if (intent === "tour") return "Theme Route";
  if (intent === "recommend_tour") return "Recommended Tour";
  return "Clarification";
}
