import type { FeatureCollection, Geometry } from "geojson";
const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
export type DecisionWeights = {
  population: number;
  vulnerability: number;
  equity: number;
};
export type DecisionResult = {
  method: string;
  theme: string;
  theme_label: string;
  has_actionable_gain: boolean;
  decision_message?: string | null;
  data_status: string;
  current_access_rate: number;
  scenario_access_rate: number;
  gained_people: number;
  underserved_people: number;
  equity_gain: number;
  facilities: FeatureCollection;
  demand_grid: FeatureCollection;
  candidates: FeatureCollection;
  current_service_area: Geometry;
  scenario_service_area: Geometry;
  recommendation: {
    rank: number;
    score: number;
    gained_people: number;
    longitude: number;
    latitude: number;
    explanation: string;
    parcel_id?: string;
    parcel_area_m2?: number;
    planning_zone?: string;
  };
  sources: { name: string; provider: string }[];
  limitations: string[];
};
export async function runSiteSelection(input: {
  territoryGeometry: Geometry;
  territoryName: string;
  territoryCode: string;
  population: number;
  theme: string;
  mode: string;
  thresholdMinutes: number;
  weights: DecisionWeights;
  equipmentLayerId?: string;
}): Promise<DecisionResult> {
  const response = await fetch(`${baseUrl}/api/v1/decisions/site-selection`, {
    method: "POST",
    body: JSON.stringify({
      territory_geometry: input.territoryGeometry,
      territory_name: input.territoryName,
      territory_code: input.territoryCode,
      population: input.population,
      theme: input.theme,
      mode: input.mode,
      threshold_minutes: input.thresholdMinutes,
      weights: input.weights,
      equipment_layer_id: input.equipmentLayerId,
    }),
    headers: {
      "Content-Type": "application/json",
      ...(sessionStorage.getItem("geodashboard-session")
        ? { "X-Session-ID": sessionStorage.getItem("geodashboard-session")! }
        : {}),
    },
  });
  const body = (await response.json()) as DecisionResult | { detail?: string };
  if (!response.ok)
    throw new Error(
      "detail" in body ? body.detail : "L’étude n’a pas pu être calculée.",
    );
  return body as DecisionResult;
}

export async function downloadDecisionReport(input: {
  territory: { name: string; code: string; area_km2: number; population: number | null; geometry: Geometry };
  decision: DecisionResult;
  mode: string;
  thresholdMinutes: number;
  weights: DecisionWeights;
}): Promise<void> {
  const response = await fetch(`${baseUrl}/api/v1/restitution/decision-reports`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      territory: {
        name: input.territory.name,
        code: input.territory.code,
        area_km2: input.territory.area_km2,
        population: input.territory.population,
      },
      territory_geometry: input.territory.geometry,
      decision: input.decision,
      mode: input.mode,
      threshold_minutes: input.thresholdMinutes,
      weights: input.weights,
    }),
  });
  if (!response.ok) throw new Error("Le rapport PDF n'a pas pu être généré.");
  const blob = await response.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `terriscope-${input.territory.code}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(link.href);
}
