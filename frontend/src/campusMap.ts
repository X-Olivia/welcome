import rawPointData from "../../backend/map/campus_points_full.json";
import campusMapImage from "../../backend/map/map.png";
import type { MapPoint, PlaceCard } from "./api";

type RawPoint = { id: string; x: number; y: number };
type RawPointData = {
  image_size: { width: number; height: number };
  points: RawPoint[];
};

type Coord = { x: number; y: number };

export interface DisplayPoi {
  id: string;
  name: string;
  area: string;
  description: string;
  relation: string;
  blurb: string;
  pointId: string;
}

const pointData = rawPointData as RawPointData;
const pointLookup = new Map(pointData.points.map((point) => [point.id, { x: point.x, y: point.y }]));

function point(id: string): Coord {
  const value = pointLookup.get(id);
  if (!value) throw new Error(`Unknown campus point: ${id}`);
  return value;
}

function distance(a: Coord, b: Coord): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

export const mapAsset = campusMapImage;
export const mapSize = pointData.image_size;

export const guideStation = {
  id: "guide-station",
  label: "AI Guide Station",
  x: point("GATE 1").x,
  y: point("GATE 1").y,
};

const displayPois: Record<string, DisplayPoi> = {
  library: {
    id: "library",
    name: "Library",
    area: "Central academic core",
    description:
      "A calm first stop for visitors who want to understand study spaces, student support, and the academic atmosphere on campus.",
    relation: "A strong stop for academic life and guided wayfinding.",
    blurb: "Quiet study atmosphere, central location, and easy access from the guide station.",
    pointId: "Library (6)",
  },
  engineering: {
    id: "engineering",
    name: "Engineering Zone",
    area: "South academic cluster",
    description:
      "This area represents the engineering and technical side of campus, making it useful for visitors curious about labs, making, and project-based learning.",
    relation: "Relevant for STEM, labs, and hands-on programme exploration.",
    blurb: "A practical stop for engineering, design, and technical learning contexts.",
    pointId: "IEB (30)",
  },
  innovation: {
    id: "innovation",
    name: "Innovation Centre",
    area: "South-east innovation cluster",
    description:
      "A route highlight for visitors interested in robotics, entrepreneurial projects, and the more future-facing side of the open day.",
    relation: "Strong match for AI, robotics, innovation, and project showcases.",
    blurb: "A good place to connect robotics, innovation culture, and applied AI topics.",
    pointId: "NICC (26)",
  },
  cafeteria: {
    id: "cafeteria",
    name: "Student Canteen",
    area: "Residential and student-life edge",
    description:
      "Useful when visitors want to sense campus life beyond teaching spaces, especially around food, daily routines, and the lived student experience.",
    relation: "Best for student-life routes and parent-friendly campus visits.",
    blurb: "Adds daily campus life and social atmosphere to a visit.",
    pointId: "Student Canteen (8)",
  },
};

export function getPoiByPlaceId(placeId: string): DisplayPoi | null {
  return displayPois[placeId] ?? null;
}

export function getFeaturedPois(): DisplayPoi[] {
  return Object.values(displayPois);
}

export function resolvePlacePosition(place: PlaceCard): Coord | null {
  if (typeof place.x === "number" && typeof place.y === "number") {
    return { x: place.x, y: place.y };
  }
  const fallback = displayPois[place.id];
  if (!fallback) return null;
  return point(fallback.pointId);
}

export function polylineDistance(points: MapPoint[]): number {
  if (points.length < 2) return 0;
  let total = 0;
  for (let idx = 0; idx < points.length - 1; idx += 1) {
    total += distance(points[idx], points[idx + 1]);
  }
  return total;
}

export function getRouteMetrics(distancePx: number): { minutes: number } {
  const minutes = Math.max(4, Math.round(distancePx / 72));
  return { minutes };
}
