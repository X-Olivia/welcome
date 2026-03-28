import { FormEvent, useMemo, useState } from "react";
import { GuideMap } from "./GuideMap";
import { type GuideResponse, postGuide } from "./api";
import { getPoiByPlaceId, getRouteMetrics, polylineDistance } from "./campusMap";
import { useVoiceGuide } from "./voice/useVoiceGuide";

const starterPrompts = [
  "How do I get to the library?",
  "I want to explore AI and robotics.",
  "Show my family the engineering area.",
  "I want to see student life and food spots.",
];

const marqueeItems = [
  "Open Day",
  "Welcome to UNNC",
  "Generate your own route",
  "Explore the campus live",
  "Voice and text guidance",
  "Continue on your phone",
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

  async function runQuery(message: string): Promise<GuideResponse> {
    const text = message.trim();
    if (!text) throw new Error("Please enter a route request.");

    setLoading(true);
    setError(null);
    setQrVisible(false);
    try {
      const data = await postGuide(text);
      setResult(data);
      setInput(text);
      return data;
    } catch (err) {
      const messageText = err instanceof Error ? err.message : String(err);
      setError(messageText);
      throw err instanceof Error ? err : new Error(messageText);
    } finally {
      setLoading(false);
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await runQuery(input);
    } catch {
      // UI state is already updated inside runQuery.
    }
  }

  const voice = useVoiceGuide({
    onGuideRequest: runQuery,
    onTranscript: (message) => {
      setInput(message);
      setError(null);
    },
  });

  const topStop = result?.places[0];
  const topStopMeta = topStop ? getPoiByPlaceId(topStop.id) : null;
  const stopCount = result?.places.length ?? 0;
  const showTransfer = Boolean(result?.mobile_url && stopCount > 0);
  const overviewText =
    result?.route_summary_zh?.trim() || result?.reply_zh?.trim() || "Tell the guide what you want to explore.";
  const streamHeading = loading
    ? "Understanding your route"
    : result
      ? "Your route, tailored for you"
      : "A personal guide, ready when you are";
  const routeTagline =
    result?.intent === "route"
      ? "A direct route shaped around one destination."
      : result?.intent === "tour"
        ? "A themed route shaped around what you want to discover."
        : result?.intent === "recommend_tour"
          ? "A recommended route based on your interests and open-day flow."
          : "A route becomes clearer when you describe what matters to you.";

  return (
    <div className="showcase-shell">
      <div className="showcase-shell__ambient" aria-hidden="true" />
      <div className="showcase-shell__grain" aria-hidden="true" />

      <section className="showcase-marquee" aria-label="Open day highlights">
        <div className="showcase-marquee__fade" aria-hidden="true" />
        <div className="showcase-marquee__inner">
          <div className="showcase-marquee__track">
            {[0, 1].map((group) => (
              <div className="showcase-marquee__group" key={group} aria-hidden={group === 1}>
                {marqueeItems.map((item, index) => (
                  <div className="showcase-marquee__item" key={`${group}-${item}`}>
                    {index === 0 && <img src="/Nottingham_logo.png" alt="" />}
                    <span>{item}</span>
                    <span className="showcase-marquee__sep">✦</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="showcase-page">
        <header className="showcase-hero">
          <div className="showcase-hero__decor" aria-hidden="true">
            <span className="showcase-sticker showcase-sticker--sun">Open Day</span>
            <span className="showcase-sticker showcase-sticker--blue">Live route</span>
            <span className="showcase-sticker showcase-sticker--mint" />
            <span className="showcase-sticker showcase-sticker--spark">✦</span>
          </div>

          <div className="showcase-brand">
            <img
              className="showcase-brand__mark"
              src="/Nottingham_logo.png"
              alt="University of Nottingham Ningbo China"
            />
            <p className="showcase-eyebrow">UNNC Open Day</p>
            <h1 className="showcase-title">
              A campus visit,
              <span> designed around you</span>
            </h1>
            <p className="showcase-copy">
              Every visitor arrives with a different curiosity. Ask in text or by voice and the
              guide will shape a live route, then hand it over to your phone when you are ready to
              walk.
            </p>
            <div className="showcase-pill-row">
              <span className="showcase-pill showcase-pill--pink">Personal route</span>
              <span className="showcase-pill showcase-pill--blue">Live map</span>
              <span className="showcase-pill showcase-pill--green">Phone handoff</span>
            </div>
          </div>
        </header>

        <main className="showcase-layout">
          <section className="showcase-stream">
            <div className="showcase-stream__section">
              <p className="showcase-section-label">
                <span className="showcase-section-label__dot" aria-hidden="true" />
                Ask the guide
              </p>

              <form className="showcase-composer" onSubmit={onSubmit}>
                <p className="showcase-composer__hint">
                  Type a place, a theme, or the kind of visit you want. The same input area also
                  works with voice, so the experience stays direct and calm.
                </p>

                <div className="showcase-composer__field">
                  <textarea
                    id="guide-input"
                    className="showcase-composer__textarea"
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    rows={4}
                    placeholder="For example: How do I get to the library? / I want to explore AI and robotics / Show my family the engineering area"
                    disabled={loading}
                  />

                  <div className="showcase-composer__toolbar">
                    <div className="showcase-chip-row" aria-label="Suggested prompts">
                      {starterPrompts.map((prompt) => (
                        <button
                          key={prompt}
                          className="showcase-chip"
                          type="button"
                          onClick={() => {
                            setInput(prompt);
                            void runQuery(prompt).catch(() => undefined);
                          }}
                          disabled={loading}
                        >
                          {prompt}
                        </button>
                      ))}
                    </div>

                    <div className="showcase-actions">
                      <button className="showcase-button showcase-button--primary" type="submit" disabled={loading || !input.trim()}>
                        {loading ? "Planning route…" : "Generate route"}
                      </button>
                      <button
                        className={`showcase-button showcase-button--mic ${voice.isActive ? "showcase-button--mic-active" : ""}`}
                        type="button"
                        onClick={() => void voice.startOrStop()}
                        disabled={loading && !voice.isActive}
                        aria-label={voice.isActive ? "Stop voice dialogue" : "Start voice dialogue"}
                      >
                        <MicGlyph />
                      </button>
                    </div>
                  </div>
                </div>

                <div className="showcase-assistant-status">
                  <span className="showcase-assistant-status__label">
                    {voicePhaseLabel(voice.phase)}
                  </span>
                  <p>{voice.lastTranscript ? `“${voice.lastTranscript}”` : voice.statusText}</p>
                  {voice.errorText && <span className="showcase-assistant-status__error">{voice.errorText}</span>}
                </div>
              </form>
            </div>

            <div className="showcase-stream__section">
              {loading && (
                <div className="showcase-loading">
                  <p className="showcase-section-label">Understanding your route</p>
                  <div className="showcase-skeleton showcase-skeleton--wide" />
                  <div className="showcase-skeleton showcase-skeleton--mid" />
                  <div className="showcase-skeleton showcase-skeleton--panel" />
                </div>
              )}

              {!loading && error && (
                <div className="showcase-result-card showcase-result-card--error" role="alert">
                  <p className="showcase-section-label">Guide response</p>
                  <h3>Something interrupted the route</h3>
                  <p>{error}</p>
                </div>
              )}

              {!loading && !result && !error && (
                <div className="showcase-result-card">
                  <div className="showcase-route-head">
                    <div>
                      <p className="showcase-section-label">Your route will appear here</p>
                      <h3>{streamHeading}</h3>
                    </div>
                    <span className="showcase-intent-pill">Ready</span>
                  </div>
                  <p className="showcase-overview">
                    Start with one thought and the assistant will turn it into a route with pace,
                    stops, and map context that feels personal instead of generic.
                  </p>
                  <div className="showcase-note-row">
                    <span>Text or voice</span>
                    <span>Personalized sequence</span>
                    <span>Mobile continuation</span>
                  </div>
                </div>
              )}

              {!loading && result && (
                <div className="showcase-result-card">
                  <div className="showcase-route-head">
                    <div>
                      <p className="showcase-section-label">Your open day route</p>
                      <h3>{routeTagline}</h3>
                    </div>
                    <span className="showcase-intent-pill">{intentLabel(result.intent)}</span>
                  </div>

                  <p className="showcase-overview">{overviewText}</p>

                  {stopCount > 0 ? (
                    <>
                      <div className="showcase-metrics">
                        <div className="showcase-metric">
                          <span>Estimated walk</span>
                          <strong>{metrics.minutes} min</strong>
                        </div>
                        <div className="showcase-metric">
                          <span>Recommended stops</span>
                          <strong>{stopCount}</strong>
                        </div>
                        <div className="showcase-metric">
                          <span>Best for</span>
                          <strong>{audienceLabel(result.intent)}</strong>
                        </div>
                      </div>

                      <div className="showcase-stop-list">
                        {result.places.map((stop, index) => {
                          const meta = getPoiByPlaceId(stop.id);
                          return (
                            <article className="showcase-stop" key={stop.id}>
                              <span className="showcase-stop__idx">{index + 1}</span>
                              <div className="showcase-stop__body">
                                <h4>{stop.name_zh}</h4>
                                <p>{stop.blurb}</p>
                                {meta && <span className="showcase-stop__meta">{meta.area}</span>}
                              </div>
                            </article>
                          );
                        })}
                      </div>
                    </>
                  ) : (
                    <div className="showcase-note-row">
                      {starterPrompts.slice(0, 3).map((prompt) => (
                        <button
                          key={prompt}
                          className="showcase-chip"
                          type="button"
                          onClick={() => {
                            setInput(prompt);
                            void runQuery(prompt).catch(() => undefined);
                          }}
                        >
                          {prompt}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {showTransfer && (
              <div className={`showcase-handoff ${qrVisible ? "showcase-handoff--visible" : ""}`}>
                <div className="showcase-handoff__copy">
                  <p className="showcase-section-label">Continue on your phone</p>
                  <h4>Walk with it</h4>
                  <p>
                    Bring the route, the stop order, and the live map with you while you move
                    across campus.
                  </p>
                  {!qrVisible ? (
                    <button
                      className="showcase-button showcase-button--secondary"
                      type="button"
                      onClick={() => setQrVisible(true)}
                    >
                      Reveal QR code
                    </button>
                  ) : (
                    <>
                      <span className="showcase-handoff__benefit">
                        Scan to continue seamlessly on your phone
                      </span>
                      {result?.mobile_url && <p className="showcase-handoff__link">{result.mobile_url}</p>}
                    </>
                  )}
                </div>

                <div className="showcase-qr">
                  {qrVisible && result?.qr_data_url ? (
                    <img src={result.qr_data_url} alt="Route QR code" />
                  ) : (
                    <div className="showcase-qr__placeholder">
                      <span>QR</span>
                      <p>Your route will be ready to carry.</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </section>

          <section className="showcase-mapcard">
            <div className="showcase-mapcard__head">
              <h2>Live route map</h2>
              <p>
                {stopCount > 0
                  ? `Your route begins at the guide station and first points you toward ${result?.places[0].name_zh}.`
                  : "The campus map stays visible below, so the route can arrive the moment the guide understands your request."}
              </p>
            </div>

            <GuideMap
              places={result?.places ?? []}
              routePolyline={result?.route_polyline ?? []}
              mode={loading ? "loading" : result ? "result" : "initial"}
            />

            <div className="showcase-mapcard__foot">
              {topStop
                ? `First stop: ${topStop.name_zh}${topStopMeta ? ` · ${topStopMeta.area}` : ""}. Follow the highlighted line and continue on your phone if you want to keep the route with you.`
                : "Once a route is generated, the highlighted line and numbered stops will appear here."}
            </div>
          </section>
        </main>
      </div>
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

function voicePhaseLabel(phase: ReturnType<typeof useVoiceGuide>["phase"]): string {
  if (phase === "greeting") return "Greeting";
  if (phase === "listening") return "Listening";
  if (phase === "transcribing") return "Transcribing";
  if (phase === "thinking") return "Thinking";
  if (phase === "speaking_result") return "Speaking";
  if (phase === "error") return "Try Again";
  return "Idle";
}

function MicGlyph() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9">
      <path d="M12 16.8v3.2" strokeLinecap="round" />
      <path d="M9.2 20.3h5.6" strokeLinecap="round" />
      <rect x="9" y="4.2" width="6" height="10.4" rx="3" />
      <path d="M6.8 10.7a5.2 5.2 0 0 0 10.4 0" strokeLinecap="round" />
    </svg>
  );
}
