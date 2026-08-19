import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { deleteLayer, listLayers, loadDemoLayer, uploadLayer } from "./api/layers";
import { runCoverage, type ScenarioLocation } from "./api/diagnostics";
import { getTerritory, type CommuneSummary } from "./api/territories";
import { WorkspaceShell } from "./components/WorkspaceShell";

type Health = { status: "ok"; service: string; version: string };

async function fetchHealth(): Promise<Health> {
  const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
  const response = await fetch(`${baseUrl}/api/v1/health`);
  if (!response.ok) throw new Error("API indisponible");
  return response.json() as Promise<Health>;
}

export function App() {
  const [selected, setSelected] = useState<CommuneSummary | null>(null);
  const [visibleIds, setVisibleIds] = useState<Set<string>>(new Set());
  const [selectedLayerId, setSelectedLayerId] = useState<string | null>(null);
  const [diagnosticLayerId, setDiagnosticLayerId] = useState("");
  const [distance, setDistance] = useState(500);
  const [scenarioLocations, setScenarioLocations] = useState<ScenarioLocation[]>([]);
  const [placingScenario, setPlacingScenario] = useState(false);
  const [expertOpen, setExpertOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const discoveredLayers = useRef<Set<string>>(new Set());
  const queryClient = useQueryClient();
  const health = useQuery({ queryKey: ["health"], queryFn: fetchHealth });
  const territory = useQuery({ queryKey: ["territory", selected?.code], queryFn: () => getTerritory(selected!.code), enabled: selected !== null });
  const layers = useQuery({ queryKey: ["layers"], queryFn: listLayers, enabled: selected !== null });
  useEffect(() => {
    const unseen = (layers.data ?? []).filter((layer) => !discoveredLayers.current.has(layer.id));
    if (!unseen.length) return;
    unseen.forEach((layer) => discoveredLayers.current.add(layer.id));
    setVisibleIds((current) => new Set([...current, ...unseen.map((layer) => layer.id)]));
  }, [layers.data]);
  const upload = useMutation({
    mutationFn: ({ file, crs }: { file: File; crs?: string }) => uploadLayer(file, crs),
    onSuccess: (layer) => {
      void queryClient.invalidateQueries({ queryKey: ["layers"] });
      setVisibleIds((current) => new Set(current).add(layer.id));
      setSelectedLayerId(layer.id);
    },
  });
  const demo = useMutation({ mutationFn: loadDemoLayer, onSuccess: (layer) => {
    void queryClient.invalidateQueries({ queryKey: ["layers"] });
    setVisibleIds((current) => new Set(current).add(layer.id));
    setSelectedLayerId(layer.id);
    setDiagnosticLayerId(layer.id);
  } });
  const remove = useMutation({ mutationFn: deleteLayer, onSuccess: (_, id) => {
    void queryClient.invalidateQueries({ queryKey: ["layers"] });
    setVisibleIds((current) => { const next = new Set(current); next.delete(id); return next; });
    setSelectedLayerId((current) => current === id ? null : current);
  } });
  const diagnostic = useMutation({ mutationFn: () => runCoverage({
    layerId: diagnosticLayerId,
    territoryGeometry: territory.data!.geometry,
    distanceM: distance,
    population: territory.data!.population,
    scenarioLocations,
  }) });
  const toggleLayer = (id: string) => setVisibleIds((current) => {
    const next = new Set(current);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });
  return <WorkspaceShell
    apiState={health.isSuccess ? "online" : health.isError ? "offline" : "loading"}
    territory={territory.data ?? null}
    territoryLoading={territory.isFetching}
    territoryError={territory.error?.message ?? null}
    onTerritorySelect={setSelected}
    layers={layers.data ?? []}
    visibleIds={visibleIds}
    selectedLayerId={selectedLayerId}
    dataError={upload.error?.message ?? demo.error?.message ?? layers.error?.message ?? null}
    uploading={upload.isPending || demo.isPending}
    onUpload={(file, crs) => upload.mutate({ file, crs })}
    onToggleLayer={toggleLayer}
    onSelectLayer={setSelectedLayerId}
    onDeleteLayer={(id) => remove.mutate(id)}
    onLoadDemo={() => demo.mutate()}
    diagnosticLayerId={diagnosticLayerId}
    diagnosticDistance={distance}
    scenarioLocations={scenarioLocations}
    placingScenario={placingScenario}
    diagnosticRunning={diagnostic.isPending}
    diagnosticError={diagnostic.error?.message ?? null}
    diagnosticResult={diagnostic.data ?? null}
    onDiagnosticLayerChange={setDiagnosticLayerId}
    onDiagnosticDistanceChange={setDistance}
    onPlaceScenarioToggle={() => setPlacingScenario((current) => !current)}
    onScenarioMapClick={(location) => { setScenarioLocations((current) => [...current, location]); setPlacingScenario(false); }}
    onClearScenario={() => { setScenarioLocations([]); diagnostic.reset(); }}
    onRunDiagnostic={() => diagnostic.mutate()}
    expertOpen={expertOpen}
    onOpenExpert={() => setExpertOpen(true)}
    onCloseExpert={() => setExpertOpen(false)}
    onLayerUpdated={() => void queryClient.invalidateQueries({ queryKey: ["layers"] })}
    reportOpen={reportOpen}
    onOpenReport={() => setReportOpen(true)}
    onCloseReport={() => setReportOpen(false)}
  />;
}
