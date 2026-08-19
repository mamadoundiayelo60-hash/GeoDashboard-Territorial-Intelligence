import type { LayerSummary } from "./layers";

const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const headers = () => ({ "Content-Type": "application/json", "X-Session-ID": sessionStorage.getItem("geodashboard-session") ?? "" });

export type HistoryEvent = { id: string; event_type: string; summary: string; parameters: Record<string, unknown>; created_at: string };
export type SqlResult = { columns: string[]; rows: unknown[][]; row_count: number; truncated: boolean; duration_ms: number };

async function json<T>(response: Response): Promise<T> {
  const body = (await response.json()) as T | { detail?: string };
  if (!response.ok) throw new Error(typeof body === "object" && body && "detail" in body ? body.detail : "L’opération experte a échoué.");
  return body as T;
}

export async function createCalculatedField(layerId: string, fieldName: string, expression: string): Promise<{ layer: LayerSummary; field_name: string; preview: unknown[] }> {
  return json(await fetch(`${baseUrl}/api/v1/expert/calculated-fields`, { method: "POST", headers: headers(), body: JSON.stringify({ layer_id: layerId, field_name: fieldName, expression }) }));
}

export async function executeSql(query: string): Promise<SqlResult> {
  return json(await fetch(`${baseUrl}/api/v1/expert/sql`, { method: "POST", headers: headers(), body: JSON.stringify({ query }) }));
}

export async function getHistory(): Promise<HistoryEvent[]> {
  return json(await fetch(`${baseUrl}/api/v1/expert/history`, { headers: { "X-Session-ID": sessionStorage.getItem("geodashboard-session") ?? "" } }));
}
