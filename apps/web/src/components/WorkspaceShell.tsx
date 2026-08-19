import { lazy, Suspense } from "react";
import type { LayerSummary } from "../api/layers";
import type { CoverageResult, ScenarioLocation } from "../api/diagnostics";
import type { CommuneSummary, TerritoryProfile } from "../api/territories";
import { DataWorkspace } from "./DataWorkspace";
import { LayerInspector } from "./LayerInspector";
import { DiagnosticStudio } from "./DiagnosticStudio";
import { ExpertWorkspace } from "./ExpertWorkspace";
import { ReportStudio } from "./ReportStudio";
import { TerritoryProfileCard } from "./TerritoryProfileCard";
import { TerritorySearch } from "./TerritorySearch";

const MapCanvas = lazy(() => import("./MapCanvas").then((module) => ({ default: module.MapCanvas })));

type ApiState = "loading" | "online" | "offline";
type Props = {
  apiState: ApiState;
  territory: TerritoryProfile | null;
  territoryLoading: boolean;
  territoryError: string | null;
  onTerritorySelect: (commune: CommuneSummary) => void;
  layers: LayerSummary[];
  visibleIds: Set<string>;
  selectedLayerId: string | null;
  dataError: string | null;
  uploading: boolean;
  onUpload: (file: File, crs?: string) => void;
  onToggleLayer: (id: string) => void;
  onSelectLayer: (id: string) => void;
  onDeleteLayer: (id: string) => void;
  diagnosticLayerId: string;
  diagnosticDistance: number;
  scenarioLocations: ScenarioLocation[];
  placingScenario: boolean;
  diagnosticRunning: boolean;
  diagnosticError: string | null;
  diagnosticResult: CoverageResult | null;
  onDiagnosticLayerChange: (id: string) => void;
  onDiagnosticDistanceChange: (distance: number) => void;
  onPlaceScenarioToggle: () => void;
  onScenarioMapClick: (location: ScenarioLocation) => void;
  onClearScenario: () => void;
  onRunDiagnostic: () => void;
  expertOpen: boolean;
  onOpenExpert: () => void;
  onCloseExpert: () => void;
  onLayerUpdated: () => void;
  onLoadDemo: () => void;
  reportOpen: boolean;
  onOpenReport: () => void;
  onCloseReport: () => void;
};

const labels: Record<ApiState, string> = { loading: "Connexion…", online: "Moteur disponible", offline: "Moteur indisponible" };

export function WorkspaceShell({ apiState, territory, territoryLoading, territoryError, onTerritorySelect, layers, visibleIds, selectedLayerId, dataError, uploading, onUpload, onToggleLayer, onSelectLayer, onDeleteLayer, diagnosticLayerId, diagnosticDistance, scenarioLocations, placingScenario, diagnosticRunning, diagnosticError, diagnosticResult, onDiagnosticLayerChange, onDiagnosticDistanceChange, onPlaceScenarioToggle, onScenarioMapClick, onClearScenario, onRunDiagnostic, expertOpen, onOpenExpert, onCloseExpert, onLayerUpdated, onLoadDemo, reportOpen, onOpenReport, onCloseReport }: Props) {
  return <div className="workspace">
    <header className="topbar">
      <div className="brand-mark">G</div><div><strong>GeoDashboard</strong><span>Territorial Intelligence Studio</span></div>
      <nav aria-label="Étapes du projet"><button className={!territory ? "active" : "done"}>Territoire</button><button className={territory && !layers.length ? "active" : layers.length ? "done" : ""}>Données</button><button className={layers.length ? "active" : ""}>Diagnostic</button><button className={diagnosticResult ? "active" : ""}>Scénarios</button><button>Restitution</button></nav>
      <div className={`api-state ${apiState}`}>{labels[apiState]}</div>
    </header>
    <aside className="layers-panel">
      <p className="panel-kicker">PROJET ACTIF</p><h1>{territory?.name ?? "Nouveau diagnostic"}</h1>
      <p>{territory ? `Territoire ${territory.code}` : "Sélectionnez un territoire pour démarrer l'analyse."}</p>
      <div className="layer-row active"><i /><span><strong>Limite communale</strong><small>{territory ? "Référentiel national" : "En attente"}</small></span></div>
      {territory ? <DataWorkspace layers={layers} visibleIds={visibleIds} selectedId={selectedLayerId} uploading={uploading} error={dataError} onUpload={onUpload} onToggle={onToggleLayer} onSelect={onSelectLayer} onDelete={onDeleteLayer} onOpenExpert={onOpenExpert} onLoadDemo={onLoadDemo} /> : <div className="empty-state"><span>02</span><strong>Les données du diagnostic apparaîtront ici</strong></div>}
    </aside>
    <main className="map-stage" aria-label="Espace cartographique">
      <Suspense fallback={<div className="map-loading">Chargement de la carte…</div>}><MapCanvas territory={territory} layers={layers} visibleIds={visibleIds} diagnostic={diagnosticResult} scenarioLocations={scenarioLocations} placingScenario={placingScenario} onScenarioMapClick={onScenarioMapClick} /></Suspense>
      {!territory && <div className="map-overlay"><TerritorySearch onSelect={onTerritorySelect} /></div>}
      {territoryLoading && <div className="map-loading">Construction du profil territorial…</div>}
      {territoryError && <div className="map-error">{territoryError}</div>}
      <div className="coordinates">EPSG:4326 · API Découpage administratif</div>
      {expertOpen && <ExpertWorkspace layers={layers} onClose={onCloseExpert} onLayerUpdated={onLayerUpdated} />}
      {reportOpen && territory && diagnosticResult && diagnosticLayerId && <ReportStudio territory={territory} diagnostic={diagnosticResult} layerId={diagnosticLayerId} layerName={layers.find((layer) => layer.id === diagnosticLayerId)?.name ?? "Couche source"} onClose={onCloseReport} />}
    </main>
    <aside className="decision-panel">
      <p className="panel-kicker">PARCOURS DÉCISION</p>
      {territory && layers.length ? <><DiagnosticStudio pointLayers={layers.filter((layer) => layer.geometry_types.some((type) => type.includes("Point")))} sourceId={diagnosticLayerId} distance={diagnosticDistance} scenarioLocations={scenarioLocations} placing={placingScenario} running={diagnosticRunning} error={diagnosticError} result={diagnosticResult} onSourceChange={onDiagnosticLayerChange} onDistanceChange={onDiagnosticDistanceChange} onPlaceToggle={onPlaceScenarioToggle} onClearScenario={onClearScenario} onRun={onRunDiagnostic} onOpenReport={onOpenReport} /><LayerInspector layer={layers.find((layer) => layer.id === selectedLayerId) ?? null} /></> : territory && selectedLayerId ? <LayerInspector layer={layers.find((layer) => layer.id === selectedLayerId) ?? null} /> : territory ? <><TerritoryProfileCard territory={territory} /><LayerInspector layer={null} /></> : <ol>
        <li className="current"><span>1</span><div><strong>Territoire</strong><small>Choisir et comprendre</small></div></li>
        <li><span>2</span><div><strong>Diagnostic</strong><small>Mesurer les écarts</small></div></li>
        <li><span>3</span><div><strong>Scénarios</strong><small>Tester une intervention</small></div></li>
        <li><span>4</span><div><strong>Décision</strong><small>Comparer et restituer</small></div></li>
      </ol>}
    </aside>
  </div>;
}
