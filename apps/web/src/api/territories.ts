import type { Geometry } from "geojson";

export type CommuneSummary = {
  code: string; name: string; department_code: string | null; region_code: string | null;
  postal_codes: string[]; population: number | null;
};

export type TerritoryProfile = CommuneSummary & {
  geometry: Geometry; bbox: [number, number, number, number]; area_km2: number;
  density_per_km2: number | null; source: string;
};

const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function apiRequest<T>(path: string): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? "Le service territorial ne répond pas.");
  }
  return response.json() as Promise<T>;
}

export function searchCommunes(query: string): Promise<CommuneSummary[]> {
  return apiRequest(`/api/v1/territories/search?q=${encodeURIComponent(query)}`);
}

export function getTerritory(code: string): Promise<TerritoryProfile> {
  return apiRequest(`/api/v1/territories/${encodeURIComponent(code)}`);
}
