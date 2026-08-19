import type { FeatureCollection } from "geojson";

export type QualityReport = {
  score: number;
  invalid_geometries: number;
  empty_geometries: number;
  duplicate_geometries: number;
  null_cells: number;
  warnings: string[];
};

export type LayerSummary = {
  id: string;
  name: string;
  source_format: string;
  feature_count: number;
  field_count: number;
  geometry_types: string[];
  crs: string;
  quality: QualityReport;
  preview: FeatureCollection | null;
};

const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function getSessionId(): string {
  const key = "geodashboard-session";
  const current = sessionStorage.getItem(key);
  if (current) return current;
  const created = crypto.randomUUID();
  sessionStorage.setItem(key, created);
  return created;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? "Le service de données est indisponible.");
  }
  return response.json() as Promise<T>;
}

export async function listLayers(): Promise<LayerSummary[]> {
  const response = await fetch(`${baseUrl}/api/v1/layers`, { headers: { "X-Session-ID": getSessionId() } });
  return parseResponse<LayerSummary[]>(response);
}

export async function uploadLayer(file: File, sourceCrs?: string): Promise<LayerSummary> {
  const form = new FormData();
  form.append("file", file);
  const query = sourceCrs ? `?source_crs=${encodeURIComponent(sourceCrs)}` : "";
  const response = await fetch(`${baseUrl}/api/v1/layers/upload${query}`, {
    method: "POST",
    headers: { "X-Session-ID": getSessionId() },
    body: form,
  });
  return parseResponse<LayerSummary>(response);
}

export async function loadDemoLayer(): Promise<LayerSummary> {
  const response = await fetch(`${baseUrl}/api/v1/layers/demo`, {
    method: "POST",
    headers: { "X-Session-ID": getSessionId() },
  });
  return parseResponse<LayerSummary>(response);
}

export async function deleteLayer(id: string): Promise<void> {
  const response = await fetch(`${baseUrl}/api/v1/layers/${encodeURIComponent(id)}`, {
    method: "DELETE",
    headers: { "X-Session-ID": getSessionId() },
  });
  if (!response.ok) throw new Error("La couche n’a pas pu être supprimée.");
}
