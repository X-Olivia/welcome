import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { GuideMap } from "./GuideMap";
import {
  type GuideSession,
  type Intent,
  type RoutePlanResponse,
  getSession,
  postMultiRoute,
  postRoute,
} from "./api";
import { getPoiByPlaceId, getRouteMetrics, polylineDistance } from "./campusMap";

const mobileEvents = [
  {
    title: "Lab Showcase",
    detail: "Engineering and robotics demos with short introductions from staff and students.",
  },
  {
    title: "Student Life Q&A",
    detail: "Meet current students to ask about societies, residences, and day-to-day campus life.",
  },
  {
    title: "Open Day Talks",
    detail: "A compact overview of programmes, admissions, and the international learning environment.",
  },
];

export function MobilePage() {
  const { token } = useParams<{ token: string }>();
  const [searchParams] = useSearchParams();
  const [data, setData] = useState<GuideSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activePlaceId, setActivePlaceId] = useState<string | null>(null);
  const [eventsOpen, setEventsOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        setError(null);
        const response = token
          ? await getSession(token)
          : await loadRouteFromSearchParams(searchParams);
        if (!cancelled) {
          setData(response);
          setActivePlaceId(response.places[0]?.id ?? null);
        }
      } catch (err) {
        if (!cancelled) {
          setData(null);
          setError(err instanceof Error ? err.message : String(err));
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [searchParams, token]);

  const routeDistance = useMemo(
    () => data?.route_distance_px ?? polylineDistance(data?.route_polyline ?? []),
    [data],
  );
  const metrics = useMemo(() => getRouteMetrics(routeDistance), [routeDistance]);
  const activeStop = activePlaceId ? getPoiByPlaceId(activePlaceId) : null;

  if (error) {
    return (
      <div className="mobile-shell">
        <section className="mobile-error-card">
          <p className="panel__eyebrow">Session Unavailable</p>
          <h1>This route is no longer available</h1>
          <p>{error}</p>
          <Link className="primary-button primary-button--link" to="/">
            Return to the guide screen
          </Link>
        </section>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="mobile-shell">
        <section className="mobile-loading">
          <p className="panel__eyebrow">Loading Route</p>
          <h1>Preparing your mobile guide</h1>
          <div className="loading-line loading-line--wide" />
          <div className="loading-line" />
        </section>
      </div>
    );
  }

  const title = data.places.length > 0 ? data.places[0].name_zh : "Campus Route";
  const summary = data.route_summary_zh?.trim() || data.reply_zh?.trim() || "Campus open day route";

  return (
    <div className="mobile-shell">
      <header className="mobile-header">
        <div>
          <p className="eyebrow">UNNC Open Day</p>
          <h1>Your Campus Route</h1>
        </div>
        <div className="mobile-header__meta">
          <span>{title}</span>
          <span>
            {metrics.minutes} min · {data.places.length} stops
          </span>
        </div>
      </header>

      <section className="mobile-map-card">
        <div className="mobile-map-card__top">
          <div>
            <p className="panel__eyebrow">Route View</p>
            <h2>{data.places.length > 1 ? "Open Day Guided Tour" : title}</h2>
          </div>
          <span className="mobile-badge">
            {data.intent === "tour"
              ? "Theme Route"
              : data.intent === "recommend_tour"
                ? "Recommended Tour"
                : data.intent === "clarification"
                  ? "Need Clarification"
                  : "Guide Route"}
          </span>
        </div>

        <GuideMap
          places={data.places}
          routePolyline={data.route_polyline}
          mode="mobile"
          activePlaceId={activePlaceId}
          onMarkerSelect={(placeId) => {
            setEventsOpen(false);
            setActivePlaceId(placeId);
          }}
        />
      </section>

      <section className="mobile-summary-card">
        <p className="panel__eyebrow">Guide Summary</p>
        <h2>{summary}</h2>
        <div className="mobile-pill-row">
          <span className="mobile-pill">
            Best for {data.intent === "tour" ? "topic discovery" : data.intent === "recommend_tour" ? "first visits" : "quick visits"}
          </span>
          <span className="mobile-pill">Start at guide station</span>
          <span className="mobile-pill">Tap map points for details</span>
        </div>
      </section>

      <section className="mobile-stops-card">
        <div className="mobile-stops-card__header">
          <div>
            <p className="panel__eyebrow">Recommended Stops</p>
            <h2>What you will see on this route</h2>
          </div>
          <span className="mobile-stops-card__count">{data.places.length}</span>
        </div>

        <div className="mobile-stop-list">
          {data.places.map((place, index) => {
            const meta = getPoiByPlaceId(place.id);
            const isActive = activePlaceId === place.id;
            return (
              <button
                key={place.id}
                className={`mobile-stop-card ${isActive ? "mobile-stop-card--active" : ""}`}
                type="button"
                onClick={() => {
                  setEventsOpen(false);
                  setActivePlaceId(place.id);
                }}
              >
                <span className="mobile-stop-card__index">{index + 1}</span>
                <span className="mobile-stop-card__content">
                  <strong>{place.name_zh}</strong>
                  <span>{place.blurb}</span>
                  {meta && <span className="mobile-stop-card__relation">{meta.relation}</span>}
                </span>
              </button>
            );
          })}
        </div>
      </section>

      <div className="sticky-action-bar">
        <div>
          <p>Campus Activities</p>
          <span>Open day events and on-site highlights</span>
        </div>
        <button
          className="primary-button"
          type="button"
          onClick={() => {
            setActivePlaceId(null);
            setEventsOpen(true);
          }}
        >
          View Open Day Events
        </button>
      </div>

      {activeStop && !eventsOpen && (
        <section className="bottom-sheet">
          <div className="bottom-sheet__handle" />
          <div className="bottom-sheet__header">
            <div>
              <p className="panel__eyebrow">Point Details</p>
              <h3>{activeStop.name}</h3>
            </div>
            <button className="sheet-close" type="button" onClick={() => setActivePlaceId(null)}>
              Close
            </button>
          </div>
          <p>{activeStop.description}</p>
          <p className="bottom-sheet__relation">{activeStop.relation}</p>
          <div className="bottom-sheet__meta">
            <span>{activeStop.area}</span>
            <span>Worth a stop</span>
          </div>
        </section>
      )}

      {eventsOpen && (
        <section className="bottom-sheet">
          <div className="bottom-sheet__handle" />
          <div className="bottom-sheet__header">
            <div>
              <p className="panel__eyebrow">Campus Activities</p>
              <h3>Open Day highlights nearby</h3>
            </div>
            <button className="sheet-close" type="button" onClick={() => setEventsOpen(false)}>
              Close
            </button>
          </div>
          <div className="events-list">
            {mobileEvents.map((eventItem) => (
              <article className="event-card" key={eventItem.title}>
                <h4>{eventItem.title}</h4>
                <p>{eventItem.detail}</p>
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

async function loadRouteFromSearchParams(searchParams: URLSearchParams): Promise<GuideSession> {
  const rawWaypoints = (searchParams.get("waypoints") ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  if (rawWaypoints.length === 0) {
    throw new Error("链接中没有可恢复的路线点位。请重新生成二维码。");
  }

  const rawMode = searchParams.get("mode");
  const mode = normalizeIntent(rawMode, rawWaypoints.length);
  const response =
    mode === "route" && rawWaypoints.length === 1
      ? await postRoute(rawWaypoints[0])
      : await postMultiRoute(rawWaypoints, mode);

  return routePlanToGuideSession(response);
}

function normalizeIntent(rawMode: string | null, waypointCount: number): Intent {
  if (rawMode === "route" || rawMode === "tour" || rawMode === "recommend_tour") {
    return rawMode;
  }
  return waypointCount <= 1 ? "route" : "tour";
}

function routePlanToGuideSession(response: RoutePlanResponse): GuideSession {
  return {
    intent: response.mode,
    reply_zh: response.summary,
    arm_action: response.arm_action,
    places: response.waypoints,
    route_summary_zh: response.summary,
    route_polyline: response.path,
    route_distance_px: response.route_distance_px,
  };
}
