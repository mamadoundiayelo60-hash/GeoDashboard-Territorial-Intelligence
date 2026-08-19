import type { Geometry } from "geojson";

export type ScenarioLocation = { longitude: number; latitude: number };
export type CoverageIndicators = {
  equipment_count: number;
  covered_area_km2: number;
  uncovered_area_km2: number;
  coverage_rate: number;
  estimated_covered_population: number | null;
};
export type CoverageResult = {
  method: string;
  distance_m: number;
  current: CoverageIndicators;
  scenario: CoverageIndicators;
  gain_points: number;
  covered_geometry: Geometry;
  uncovered_geometry: Geometry;
  scenario_covered_geometry: Geometry;
  scenario_uncovered_geometry: Geometry;
  interpretation: string;
  warnings: string[];
};

const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function sessionId(): string {
  return sessionStorage.getItem("geodashboard-session") ?? "";
}

export async function runCoverage(input: {
  layerId: string;
  territoryGeometry: Geometry;
  distanceM: number;
  population: number | null;
  scenarioLocations: ScenarioLocation[];
}): Promise<CoverageResult> {
  const response = await fetch(`${baseUrl}/api/v1/diagnostics/coverage`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Session-ID": sessionId() },
    body: JSON.stringify({ layer_id: input.layerId, territory_geometry: input.territoryGeometry, distance_m: input.distanceM, population: input.population, scenario_locations: input.scenarioLocations }),
  });
  const body = (await response.json()) as CoverageResult | { detail?: string };
  if (!response.ok) throw new Error("detail" in body ? body.detail : "Le diagnostic a échoué.");
  return body as CoverageResult;
}
