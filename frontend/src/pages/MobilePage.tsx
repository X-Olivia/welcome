import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { type GuideSession, type Intent, type MapPoint, type RoutePlanResponse, getSession, postGuide, postMultiRoute, postRoute } from "../api";
import { GuideMap } from "../GuideMap";
import { BottomTabBar, type MobileTab } from "../components/BottomTabBar";
import { MapControls } from "../components/MapControls";
import { PlaceCard } from "../components/PlaceCard";
import { TopBar } from "../components/TopBar";
import {
  getPoiByPlaceId,
  getRouteMetrics,
  guideStation,
  mapSize,
  polylineDistance,
  resolvePlacePosition,
} from "../campusMap";
import { ActivityPage, type ActivityFilter } from "./ActivityPage";
import { NewsPage } from "./NewsPage";

const INITIAL_ZOOM = 1.9;
const MIN_ZOOM = 1.3;
const MAX_ZOOM = 2.4;

export function MobilePage() {
  const { token } = useParams<{ token: string }>();
  const [searchParams] = useSearchParams();
  const [data, setData] = useState<GuideSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<MobileTab>("map");
  const [selectedPlaceId, setSelectedPlaceId] = useState<string | null>(null);
  const [isCardOpen, setIsCardOpen] = useState(false);
  const [newsQuery, setNewsQuery] = useState("");
  const [activityFilter, setActivityFilter] = useState<ActivityFilter>("today");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [zoom, setZoom] = useState(INITIAL_ZOOM);
  const [viewportCenter, setViewportCenter] = useState<MapPoint | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        setError(null);
        const response = token
          ? await getSession(token)
          : await loadRouteFromSearchParams(searchParams);
        if (!cancelled) {
          applyGuideSession(response);
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

  const userLocation = useMemo<MapPoint>(() => {
    if (data?.route_polyline?.[0]) return data.route_polyline[0];
    return { x: guideStation.x, y: guideStation.y };
  }, [data]);

  const selectedRoutePlace = useMemo(() => {
    if (!data || !selectedPlaceId) return null;
    return data.places.find((place) => place.id === selectedPlaceId) ?? null;
  }, [data, selectedPlaceId]);

  const selectedPoi = useMemo(() => {
    if (!selectedPlaceId) return null;
    return getPoiByPlaceId(selectedPlaceId);
  }, [selectedPlaceId]);

  const selectedPlacePresentation = useMemo(() => {
    if (!selectedPlaceId) return null;
    const meta = selectedPoi;
    const fallbackTitle = selectedRoutePlace?.name_zh ?? selectedPlaceId;
    return {
      title: meta?.name ?? fallbackTitle,
      description:
        meta?.description ??
        selectedRoutePlace?.blurb ??
        `${fallbackTitle} is available as a marked stop on the campus map.`,
      meta:
        meta?.relation ??
        "This stop is available on the map and can be explored as part of your campus visit.",
      tag: meta?.area ?? "Campus stop",
    };
  }, [selectedPlaceId, selectedPoi, selectedRoutePlace]);

  const title = data?.places[0]?.name_zh || "Campus Route";
  const summary = (
    data?.route_summary_zh?.trim() ||
    data?.reply_zh?.trim() ||
    "A clean, guided route is ready for you."
  ).trim();

  if (error) {
    return (
      <div className="mobile-app mobile-app--plain">
        <section className="mobile-state-card mobile-state-card--error">
          <p className="panel__eyebrow">Session unavailable</p>
          <h1>This route could not be restored</h1>
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
      <div className="mobile-app mobile-app--plain">
        <section className="mobile-state-card">
          <p className="panel__eyebrow">Loading route</p>
          <h1>Preparing your mobile guide</h1>
          <div className="loading-line loading-line--wide" />
          <div className="loading-line" />
        </section>
      </div>
    );
  }

  return (
    <div className="mobile-app">
      <div className="mobile-app__viewport">
        {activeTab === "map" ? (
          <div className="mobile-map-screen">
            <GuideMap
              className="guide-map--mobile-immersive"
              places={data.places}
              routePolyline={data.route_polyline}
              mode="mobile"
              activePlaceId={selectedPlaceId}
              onMarkerSelect={handleMarkerSelect}
              hideChrome
              zoom={zoom}
              viewportCenter={viewportCenter ?? userLocation}
              userLocation={userLocation}
              onViewportPan={(deltaX, deltaY, bounds) => {
                setViewportCenter((current) => {
                  const base = current ?? userLocation;
                  const nextX = base.x - (deltaX / bounds.width) * mapSize.width / zoom;
                  const nextY = base.y - (deltaY / bounds.height) * mapSize.height / zoom;
                  return {
                    x: clamp(nextX, 0, mapSize.width),
                    y: clamp(nextY, 0, mapSize.height),
                  };
                });
              }}
            />

            <div className="mobile-map-screen__top">
              <TopBar />
              <div className="mobile-route-banner mobile-glass">
                <div className="mobile-route-banner__copy">
                  <span className="mobile-route-banner__eyebrow">{intentLabel(data.intent)}</span>
                  <strong>{data.places.length > 1 ? "Open Day Route" : title}</strong>
                  <p>{trimCopy(summary, 104)}</p>
                </div>
                <div className="mobile-route-banner__stats">
                  <span>{metrics.minutes} min</span>
                  <span>{data.places.length} stops</span>
                </div>
              </div>
            </div>

            <MapControls
              onZoomIn={() => setZoom((current) => Math.min(MAX_ZOOM, roundZoom(current + 0.18)))}
              onZoomOut={() => setZoom((current) => Math.max(MIN_ZOOM, roundZoom(current - 0.18)))}
              onLocate={centerOnUser}
              canZoomIn={zoom < MAX_ZOOM}
              canZoomOut={zoom > MIN_ZOOM}
            />

            {selectedPlacePresentation && isCardOpen && (
              <PlaceCard
                title={selectedPlacePresentation.title}
                description={selectedPlacePresentation.description}
                meta={selectedPlacePresentation.meta}
                tag={selectedPlacePresentation.tag}
                isOpen={isCardOpen}
                onClose={() => setIsCardOpen(false)}
                onGo={focusSelectedPlace}
              />
            )}
          </div>
        ) : (
          <div className="mobile-panel-screen">
            <TopBar />
            {activeTab === "activity" ? (
              <ActivityPage
                filter={activityFilter}
                onFilterChange={setActivityFilter}
                onConfirm={() => void submitGuideRequest(promptForActivityFilter(activityFilter))}
                isSubmitting={isSubmitting}
              />
            ) : (
              <NewsPage query={newsQuery} onQueryChange={setNewsQuery} />
            )}
          </div>
        )}

        <BottomTabBar
          activeTab={activeTab}
          onChange={(tab) => {
            setActiveTab(tab);
            if (tab !== "map") setIsCardOpen(false);
          }}
        />
      </div>
    </div>
  );

  async function submitGuideRequest(rawMessage: string) {
    const message = rawMessage.trim();
    if (!message) return;

    setIsSubmitting(true);
    setError(null);
    try {
      const response = await postGuide(message);
      applyGuideSession(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  function applyGuideSession(session: GuideSession) {
    setData(session);
    setActiveTab("map");
    setSelectedPlaceId(null);
    setIsCardOpen(false);
    setViewportCenter(getUserLocationForSession(session));
    setZoom(INITIAL_ZOOM);
  }

  function handleMarkerSelect(placeId: string) {
    setSelectedPlaceId(placeId);
    setIsCardOpen(true);
    const routePlace = data?.places.find((item) => item.id === placeId) ?? null;
    const position = routePlace
      ? resolvePlacePosition(routePlace)
      : resolvePlacePosition({ id: placeId, name_zh: placeId, blurb: "" });
    if (position) {
      setViewportCenter(position);
      setZoom((current) => Math.max(current, 1.85));
    }
  }

  function focusSelectedPlace() {
    if (!selectedPlaceId) return;
    const routePlace = data?.places.find((item) => item.id === selectedPlaceId) ?? null;
    const position = routePlace
      ? resolvePlacePosition(routePlace)
      : resolvePlacePosition({ id: selectedPlaceId, name_zh: selectedPlaceId, blurb: "" });
    if (position) {
      setViewportCenter(position);
      setZoom((current) => Math.max(current, 1.95));
    }
  }

  function centerOnUser() {
    setViewportCenter(userLocation);
    setZoom(INITIAL_ZOOM);
  }
}

function getUserLocationForSession(session: GuideSession): MapPoint {
  return session.route_polyline[0] ?? { x: guideStation.x, y: guideStation.y };
}

function trimCopy(text: string, maxLength: number) {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (normalized.length <= maxLength) return normalized;
  return `${normalized.slice(0, maxLength - 1)}…`;
}

function roundZoom(value: number) {
  return Math.round(value * 100) / 100;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function promptForActivityFilter(filter: ActivityFilter) {
  if (filter === "scheduled") {
    return "Recommend a campus route for scheduled open day highlights and the main hall.";
  }
  if (filter === "upcoming") {
    return "Recommend a route for upcoming open day highlights around innovation and admissions.";
  }
  return "Recommend a campus route for today's open day activities.";
}

function intentLabel(intent: Intent) {
  if (intent === "tour") return "Theme route";
  if (intent === "recommend_tour") return "Recommended route";
  if (intent === "clarification") return "Need details";
  return "Direct route";
}

async function loadRouteFromSearchParams(searchParams: URLSearchParams): Promise<GuideSession> {
  const rawWaypoints = (searchParams.get("waypoints") ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  if (rawWaypoints.length === 0) {
    throw new Error("This link does not contain recoverable route waypoints. Please generate the QR code again.");
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
