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

function titleCaseWords(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b([a-z])/gi, (match) => match.toUpperCase());
}

function readablePointName(id: string): string {
  return titleCaseWords(id.replace(/\(([^)]+)\)/g, "").replace(/\b([A-Z])\s+/g, "$1 ").trim());
}

function areaForPoint(id: string): string {
  if (/gate/i.test(id)) return "Campus entrance";
  if (/library/i.test(id)) return "Central academic core";
  if (/pmb|yfj|yang fujia|ieb|iamet|nicc|db|new audi/i.test(id)) return "Engineering and innovation";
  if (/canteen|hub|residence|villa|hotel|apartments|space/i.test(id)) return "Student life and living";
  if (/sports|health|wellbeing/i.test(id)) return "Sports and wellbeing";
  if (/museum|admission|recruitment/i.test(id)) return "Visitor information";
  if (/garden/i.test(id)) return "Campus landscape";
  return "Campus location";
}

function genericPoiForPoint(id: string): DisplayPoi {
  const name = readablePointName(id);
  return {
    id,
    name,
    area: areaForPoint(id),
    description: `${name} is available as a marked campus point on the guide map and can be included as a reference stop while visitors explore the site.`,
    relation: "Tap the marker to inspect this campus location.",
    blurb: `Marked campus point for ${name}.`,
    pointId: id,
  };
}

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
  x: point("IEB (30)").x,
  y: point("IEB (30)").y,
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
    name: "IEB",
    area: "South academic cluster",
    description:
      "This area represents the engineering and technical side of campus, making it useful for visitors curious about labs, making, and project-based learning.",
    relation: "Relevant for STEM, labs, and hands-on programme exploration.",
    blurb: "A practical stop for engineering, design, and technical learning contexts.",
    pointId: "IEB (30)",
  },
  pmb: {
    id: "pmb",
    name: "Portland Building (PMB)",
    area: "Engineering and innovation",
    description:
      "PMB is one of the clearest entry points into the engineering side of campus, with teaching and project spaces that help visitors understand how technical programmes are taught in practice.",
    relation: "A strong anchor for engineering, STEM, and applied-learning routes.",
    blurb: "A useful first stop for visitors exploring engineering, design, and technical study spaces.",
    pointId: "PMB (2)",
  },
  yang_fujia: {
    id: "yang_fujia",
    name: "YANG Fujia Building",
    area: "Engineering and innovation",
    description:
      "YANG Fujia Building sits close to the academic core and works well as a bridge between central teaching spaces and the engineering-focused southern cluster.",
    relation: "Useful in routes that connect academic atmosphere with engineering exploration.",
    blurb: "A central stop that helps connect core academic spaces with the wider engineering route.",
    pointId: "YANG Fujia (3)",
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
  nicc: {
    id: "nicc",
    name: "NICC",
    area: "Engineering and innovation",
    description:
      "NICC is a strong showcase stop for innovation projects, interdisciplinary making, and the more future-facing side of the campus experience.",
    relation: "Best suited to AI, robotics, innovation, and entrepreneurship-themed routes.",
    blurb: "A strong stop for visitors interested in innovation culture, robotics, and applied project work.",
    pointId: "NICC (26)",
  },
  db: {
    id: "db",
    name: "DB Building",
    area: "Engineering and innovation",
    description:
      "DB Building extends the southern teaching cluster and helps visitors see that engineering and technical learning happen across multiple connected spaces rather than in a single landmark.",
    relation: "Useful as a supporting stop in broader engineering and innovation routes.",
    blurb: "Part of the wider southern engineering cluster and useful in multi-stop technical tours.",
    pointId: "DB (24)",
  },
  new_audi: {
    id: "new_audi",
    name: "New Audi",
    area: "Engineering and innovation",
    description:
      "New Audi often works as an event-facing support stop near the southern cluster, adding presentation and showcase context to technical or innovation routes.",
    relation: "Useful when a route blends technical exploration with talks, demos, or event-based programming.",
    blurb: "A supporting stop that helps connect engineering routes with talks, demos, and showcase activity.",
    pointId: "New Audi (25)",
  },
  iamet: {
    id: "iamet",
    name: "IAMET",
    area: "Engineering and innovation",
    description:
      "IAMET sits within the southern engineering zone and is well suited to routes focused on manufacturing, applied engineering, and practice-oriented technical learning.",
    relation: "A strong fit for engineering, making, manufacturing, and applied-technology themes.",
    blurb: "A practical stop for visitors interested in engineering application, making, and technical practice.",
    pointId: "IAMET (29)",
  },
  ieb: {
    id: "ieb",
    name: "Innovation and Enterprise Building (IEB)",
    area: "Engineering and innovation",
    description:
      "IEB is an important southern-cluster landmark for visitors interested in engineering, innovation, enterprise, and application-oriented project culture.",
    relation: "A key stop in engineering, innovation, and project-based campus tours.",
    blurb: "A major route node connecting engineering, innovation, and enterprise-focused campus experiences.",
    pointId: "IEB (30)",
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

const allCampusPois: DisplayPoi[] = pointData.points.map((raw) => {
  const curated = Object.values(displayPois).find((poi) => poi.pointId === raw.id);
  return curated ?? genericPoiForPoint(raw.id);
});

export function getPoiByPlaceId(placeId: string): DisplayPoi | null {
  return displayPois[placeId] ?? (pointLookup.has(placeId) ? genericPoiForPoint(placeId) : null);
}

export function getFeaturedPois(): DisplayPoi[] {
  return Object.values(displayPois);
}

export function getAllCampusPois(): DisplayPoi[] {
  return allCampusPois;
}

export function resolvePlacePosition(place: PlaceCard): Coord | null {
  if (typeof place.x === "number" && typeof place.y === "number") {
    return { x: place.x, y: place.y };
  }
  if (pointLookup.has(place.id)) {
    return point(place.id);
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
