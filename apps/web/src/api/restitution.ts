import type { CoverageResult } from "./diagnostics";
import type { TerritoryProfile } from "./territories";

const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const sessionHeader = () => ({ "X-Session-ID": sessionStorage.getItem("geodashboard-session") ?? "" });

export type ReportOptions = { title: string; template: "a4_portrait" | "a4_landscape" | "a3_landscape"; author: string; includeDetails: boolean; includeMethodology: boolean; includeSources: boolean };

async function download(response: Response, fallbackName: string): Promise<void> {
  if (!response.ok) { const body = (await response.json().catch(() => null)) as { detail?: string } | null; throw new Error(body?.detail ?? "Le téléchargement a échoué."); }
  const blob = await response.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob); link.download = fallbackName; document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(link.href);
}

export async function downloadReport(options: ReportOptions, territory: TerritoryProfile, diagnostic: CoverageResult, sourceLayerName: string): Promise<void> {
  const response = await fetch(`${baseUrl}/api/v1/restitution/reports`, { method: "POST", headers: { ...sessionHeader(), "Content-Type": "application/json" }, body: JSON.stringify({ title: options.title, template: options.template, territory: { name: territory.name, code: territory.code, area_km2: territory.area_km2, population: territory.population }, diagnostic, source_layer_name: sourceLayerName, author: options.author, include_details: options.includeDetails, include_methodology: options.includeMethodology, include_sources: options.includeSources }) });
  return download(response, `rapport-${territory.code}.pdf`);
}

export async function downloadLayer(layerId: string, format: "geojson" | "gpkg"): Promise<void> {
  return download(await fetch(`${baseUrl}/api/v1/restitution/layers/${encodeURIComponent(layerId)}?format=${format}`, { headers: sessionHeader() }), `couche-${layerId}.${format}`);
}

export async function downloadManifest(): Promise<void> {
  return download(await fetch(`${baseUrl}/api/v1/restitution/manifest`, { headers: sessionHeader() }), "geodashboard-manifest.json");
}
