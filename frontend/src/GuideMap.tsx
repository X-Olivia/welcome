import type { MapPoint, PlaceCard } from "./api";
import { LocationMarker } from "./components/LocationMarker";
import {
  getAllCampusPois,
  getFeaturedPois,
  guideStation,
  mapAsset,
  mapSize,
  resolvePlacePosition,
} from "./campusMap";

type GuideMapProps = {
  places: PlaceCard[];
  routePolyline?: MapPoint[];
  mode: "initial" | "loading" | "result" | "mobile";
  activePlaceId?: string | null;
  activePlaceCard?: {
    title: string;
    description: string;
    tag: string;
    relation?: string | null;
  } | null;
  onActivePlaceClose?: () => void;
  onMarkerSelect?: (placeId: string) => void;
  hideChrome?: boolean;
  zoom?: number;
  viewportCenter?: MapPoint | null;
  userLocation?: MapPoint | null;
  className?: string;
  onViewportPan?: (deltaX: number, deltaY: number, bounds: DOMRect) => void;
};

type VisibleStop = PlaceCard & { x: number; y: number };

const loadingPreview: MapPoint[] = [
  { x: guideStation.x, y: guideStation.y },
  { x: 412, y: 372 },
  { x: 596, y: 470 },
  { x: 650, y: 724 },
  { x: 742, y: 787 },
];

export function GuideMap({
  places,
  routePolyline = [],
  mode,
  activePlaceId,
  activePlaceCard,
  onActivePlaceClose,
  onMarkerSelect,
  hideChrome = false,
  zoom = 1,
  viewportCenter,
  userLocation,
  className,
  onViewportPan,
}: GuideMapProps) {
  const featuredPois = getAllCampusPois();
  const curatedPoiIds = new Set(getFeaturedPois().map((poi) => poi.id));
  const stopLookup = new Map<string, VisibleStop>();

  function offsetMarkerPosition(position: { x: number; y: number }) {
    if (position.x === guideStation.x && position.y === guideStation.y) {
      return { x: position.x + 24, y: position.y + 22 };
    }
    return position;
  }

  featuredPois.forEach((poi) => {
    const position = resolvePlacePosition({ id: poi.id, name_zh: poi.name, blurb: poi.blurb });
    if (!position) return;
    const shifted = offsetMarkerPosition(position);
    stopLookup.set(poi.id, {
      id: poi.id,
      name_zh: poi.name,
      blurb: poi.blurb,
      x: shifted.x,
      y: shifted.y,
    });
  });

  places.forEach((place) => {
    const position = resolvePlacePosition(place);
    if (!position) return;
    const shifted = offsetMarkerPosition(position);
    const existingAtPosition = Array.from(stopLookup.entries()).find(
      ([, stop]) => stop.x === shifted.x && stop.y === shifted.y,
    );
    if (existingAtPosition) {
      stopLookup.delete(existingAtPosition[0]);
    }
    stopLookup.set(place.id, { ...place, x: shifted.x, y: shifted.y });
  });

  const visibleStops = Array.from(stopLookup.values());

  const polyline = routePolyline.map((point) => `${point.x},${point.y}`).join(" ");
  const loadingPolyline = loadingPreview.map((point) => `${point.x},${point.y}`).join(" ");
  const safeScale = Math.max(1, zoom);
  const effectiveCenter = viewportCenter ?? {
    x: mapSize.width / 2,
    y: mapSize.height / 2,
  };
  const translateX = (0.5 - effectiveCenter.x / mapSize.width) * 100 * safeScale;
  const translateY = (0.5 - effectiveCenter.y / mapSize.height) * 100 * safeScale;
  const activeStop = activePlaceId ? visibleStops.find((stop) => stop.id === activePlaceId) ?? null : null;
  const anchorX = activeStop ? activeStop.x / mapSize.width : 0;
  const anchorY = activeStop ? activeStop.y / mapSize.height : 0;
  const popoverHorizontalClass = anchorX > 0.64 ? "guide-map__popover--west" : "guide-map__popover--east";
  const popoverVerticalClass =
    anchorY < 0.24
      ? "guide-map__popover--below"
      : anchorY > 0.74
        ? "guide-map__popover--above"
        : "guide-map__popover--center";

  return (
    <div className={`guide-map ${hideChrome ? "guide-map--minimal" : ""} ${className ?? ""}`.trim()}>
      <div
        className="guide-map__canvas"
        onPointerDown={(event) => {
          const source = event.target as Element | null;
          if (source?.closest(".guide-map__marker, .guide-map__popover")) {
            return;
          }

          const target = event.currentTarget;
          let lastX = event.clientX;
          let lastY = event.clientY;
          const bounds = target.getBoundingClientRect();
          target.setPointerCapture(event.pointerId);

          const handleMove = (moveEvent: PointerEvent) => {
            const deltaX = moveEvent.clientX - lastX;
            const deltaY = moveEvent.clientY - lastY;
            lastX = moveEvent.clientX;
            lastY = moveEvent.clientY;
            onViewportPan?.(deltaX, deltaY, bounds);
          };

          const handleEnd = () => {
            target.releasePointerCapture(event.pointerId);
            target.removeEventListener("pointermove", handleMove);
            target.removeEventListener("pointerup", handleEnd);
            target.removeEventListener("pointercancel", handleEnd);
          };

          target.addEventListener("pointermove", handleMove);
          target.addEventListener("pointerup", handleEnd);
          target.addEventListener("pointercancel", handleEnd);
        }}
      >
        {!hideChrome && (
          <div className="guide-map__badge">
            {visibleStops.length > 0 && routePolyline.length > 0
              ? "Route generated for this visitor"
              : "Explore the campus map"}
          </div>
        )}
        {!hideChrome && (
          <div className={`guide-map__status ${mode === "loading" ? "guide-map__status--loading" : ""}`}>
            {mode === "loading"
              ? "Planning your route"
              : routePolyline.length > 0
                ? "Route Ready"
                : "Map Overview"}
          </div>
        )}

        <div
          className="guide-map__scene"
          style={{
            transform: `translate(calc(-50% + ${translateX}%), calc(-50% + ${translateY}%)) scale(${safeScale})`,
          }}
        >
          <img src={mapAsset} alt="UNNC campus map" />

          <svg
            className="guide-map__overlay"
            viewBox={`0 0 ${mapSize.width} ${mapSize.height}`}
            aria-hidden="true"
            preserveAspectRatio="none"
          >
            <defs>
              <filter id="route-glow">
                <feGaussianBlur stdDeviation="8" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              <filter id="marker-glow">
                <feGaussianBlur stdDeviation="5" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            {mode === "loading" && loadingPolyline && (
              <polyline
                className="guide-map__ghost"
                points={loadingPolyline}
                fill="none"
                stroke="rgba(31, 103, 210, 0.46)"
                strokeWidth="18"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeDasharray="28 18"
              />
            )}

            {polyline && routePolyline.length > 1 && (
              <>
                <polyline
                  points={polyline}
                  fill="none"
                  stroke="rgba(124, 206, 214, 0.42)"
                  strokeWidth="26"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  filter="url(#route-glow)"
                />
                <polyline
                  points={polyline}
                  fill="none"
                  stroke="#0f3d91"
                  strokeWidth="12"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <polyline
                  points={polyline}
                  fill="none"
                  stroke="#ffffff"
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeDasharray="2 16"
                />
              </>
            )}

            {userLocation && <LocationMarker point={userLocation} />}

            {visibleStops.map((stop) => {
              const isActive = activePlaceId === stop.id;
              const isCore = isActive || curatedPoiIds.has(stop.id) || places.some((place) => place.id === stop.id);
              return (
              <g
                className={`guide-map__marker ${isCore ? "" : "guide-map__marker--subtle"}`.trim()}
                key={stop.id}
                onPointerUp={(event) => {
                  event.stopPropagation();
                  onMarkerSelect?.(stop.id);
                }}
                onClick={(event) => {
                  event.stopPropagation();
                }}
                role={onMarkerSelect ? "button" : undefined}
              >
                  <circle
                    cx={stop.x}
                    cy={stop.y}
                    r={isActive ? 18 : 13}
                    fill={isActive ? "rgba(86, 146, 255, 0.24)" : "rgba(86, 146, 255, 0.18)"}
                    filter="url(#marker-glow)"
                  />
                  <circle
                    cx={stop.x}
                    cy={stop.y}
                    r={isActive ? 11 : 7}
                    fill={isActive ? "#1f67d2" : "#0f3d91"}
                    stroke="#ffffff"
                    strokeWidth={isActive ? 5 : 4}
                  />
                </g>
              );
            })}

            <LocationMarker point={guideStation} variant="guide" />
          </svg>

          {activeStop && activePlaceCard && mode !== "mobile" && (
            <div
              className={`guide-map__popover ${popoverHorizontalClass} ${popoverVerticalClass}`}
              style={{
                left: `${anchorX * 100}%`,
                top: `${anchorY * 100}%`,
              }}
            >
              <div className="guide-map__popover-header">
                <div>
                  <p className="guide-map__popover-tag">{activePlaceCard.tag}</p>
                  <h4>{activePlaceCard.title}</h4>
                </div>

                <button
                  className="guide-map__popover-close"
                  type="button"
                  onClick={onActivePlaceClose}
                  aria-label="Close place introduction"
                >
                  <span aria-hidden="true">✦</span>
                </button>
              </div>

              <p className="guide-map__popover-description">{activePlaceCard.description}</p>
              {activePlaceCard.relation && (
                <span className="guide-map__popover-pill">{activePlaceCard.relation}</span>
              )}
            </div>
          )}
        </div>

        {!hideChrome && (
          <div className="guide-map__hint">
            {routePolyline.length > 0
              ? "The highlighted line shows the suggested walk. Tap a stop to read more."
              : "Key places stay visible here before a route is generated, so visitors can see the campus structure first."}
          </div>
        )}
      </div>
    </div>
  );
}
