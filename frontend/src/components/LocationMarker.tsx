import type { MapPoint } from "../api";

interface LocationMarkerProps {
  point: MapPoint;
}

export function LocationMarker({ point }: LocationMarkerProps) {
  return (
    <g className="guide-map__user-location" aria-hidden="true">
      <circle className="guide-map__user-pulse" cx={point.x} cy={point.y} r="42" />
      <circle className="guide-map__user-halo" cx={point.x} cy={point.y} r="22" />
      <circle className="guide-map__user-dot" cx={point.x} cy={point.y} r="11" />
    </g>
  );
}
