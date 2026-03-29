import type { MapPoint } from "../api";

interface LocationMarkerProps {
  point: MapPoint;
  variant?: "user" | "guide";
}

export function LocationMarker({ point, variant = "user" }: LocationMarkerProps) {
  if (variant === "guide") {
    return (
      <g className="guide-map__guide-location" aria-hidden="true">
        <circle className="guide-map__guide-pulse" cx={point.x} cy={point.y} r="44" />
        <circle className="guide-map__guide-halo" cx={point.x} cy={point.y} r="24" />
        <path
          className="guide-map__guide-pin"
          d={`M ${point.x} ${point.y + 22}
              C ${point.x + 13} ${point.y + 10}, ${point.x + 18} ${point.y - 1}, ${point.x + 18} ${point.y - 13}
              A 18 18 0 1 0 ${point.x - 18} ${point.y - 13}
              C ${point.x - 18} ${point.y - 1}, ${point.x - 13} ${point.y + 10}, ${point.x} ${point.y + 22} Z`}
        />
        <circle className="guide-map__guide-core" cx={point.x} cy={point.y - 13} r="6.5" />
      </g>
    );
  }

  return (
    <g className="guide-map__user-location" aria-hidden="true">
      <circle className="guide-map__user-pulse" cx={point.x} cy={point.y} r="42" />
      <circle className="guide-map__user-halo" cx={point.x} cy={point.y} r="22" />
      <circle className="guide-map__user-dot" cx={point.x} cy={point.y} r="11" />
    </g>
  );
}
