import type { MapPoint, PlaceCard } from "./api";
import {
  getFeaturedPois,
  getPoiByPlaceId,
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
  onMarkerSelect?: (placeId: string) => void;
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
  onMarkerSelect,
}: GuideMapProps) {
  const featuredPois = getFeaturedPois();
  const visibleStops: VisibleStop[] =
    places.length > 0
      ? places
          .map((place) => {
            const position = resolvePlacePosition(place);
            if (!position) return null;
            return { ...place, x: position.x, y: position.y };
          })
          .filter((place): place is VisibleStop => place !== null)
      : featuredPois
          .map((poi) => {
            const position = resolvePlacePosition({ id: poi.id, name_zh: poi.name, blurb: poi.blurb });
            if (!position) return null;
            return {
              id: poi.id,
              name_zh: poi.name,
              blurb: poi.blurb,
              x: position.x,
              y: position.y,
            } satisfies VisibleStop;
          })
          .filter((place): place is VisibleStop => place !== null);

  const polyline = routePolyline.map((point) => `${point.x},${point.y}`).join(" ");
  const loadingPolyline = loadingPreview.map((point) => `${point.x},${point.y}`).join(" ");

  return (
    <div className="guide-map">
      <div className="guide-map__canvas">
        <div className="guide-map__badge">
          {visibleStops.length > 0 && routePolyline.length > 0
            ? "Route generated for this visitor"
            : "Explore the campus map"}
        </div>
        <div className={`guide-map__status ${mode === "loading" ? "guide-map__status--loading" : ""}`}>
          {mode === "loading" ? "Planning your route" : routePolyline.length > 0 ? "Route Ready" : "Map Overview"}
        </div>

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

          <g>
            <circle cx={guideStation.x} cy={guideStation.y} r="26" fill="rgba(124, 206, 214, 0.22)" />
            <circle cx={guideStation.x} cy={guideStation.y} r="14" fill="#7cced6" stroke="#ffffff" strokeWidth="6" />
            <text x={guideStation.x + 34} y={guideStation.y - 12} className="guide-map__station-label">
              AI Guide Station
            </text>
          </g>

          {visibleStops.map((stop, index) => {
            const isActive = activePlaceId === stop.id;
            const meta = getPoiByPlaceId(stop.id);
            return (
              <g
                className="guide-map__marker"
                key={stop.id}
                onClick={() => onMarkerSelect?.(stop.id)}
                role={onMarkerSelect ? "button" : undefined}
              >
                <circle
                  cx={stop.x}
                  cy={stop.y}
                  r={isActive ? 34 : 28}
                  fill={isActive ? "rgba(31, 103, 210, 0.28)" : "rgba(15, 61, 145, 0.14)"}
                />
                <circle
                  cx={stop.x}
                  cy={stop.y}
                  r={isActive ? 22 : 18}
                  fill={isActive ? "#1f67d2" : "#0f3d91"}
                  stroke="#ffffff"
                  strokeWidth="6"
                />
                <text x={stop.x} y={stop.y + 1} className="guide-map__marker-label">
                  {index + 1}
                </text>
                {(mode !== "mobile" || isActive) && meta && (
                  <text x={stop.x + 36} y={stop.y - 10} className="guide-map__marker-name">
                    {meta.name}
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        <div className="guide-map__hint">
          {routePolyline.length > 0
            ? "The highlighted line shows the suggested walk. Tap a stop on mobile to read more."
            : "Key places stay visible here before a route is generated, so visitors can see the campus structure first."}
        </div>
      </div>
    </div>
  );
}
