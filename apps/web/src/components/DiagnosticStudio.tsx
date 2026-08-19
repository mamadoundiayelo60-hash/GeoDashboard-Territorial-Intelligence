import type { CoverageResult, ScenarioLocation } from "../api/diagnostics";
import type { LayerSummary } from "../api/layers";

type Props = {
  pointLayers: LayerSummary[];
  sourceId: string;
  distance: number;
  scenarioLocations: ScenarioLocation[];
  placing: boolean;
  running: boolean;
  error: string | null;
  result: CoverageResult | null;
  onSourceChange: (id: string) => void;
  onDistanceChange: (distance: number) => void;
  onPlaceToggle: () => void;
  onClearScenario: () => void;
  onRun: () => void;
  onOpenReport: () => void;
};

export function DiagnosticStudio(props: Props) {
  const { pointLayers, sourceId, distance, scenarioLocations, placing, running, error, result } = props;
  return <section className="diagnostic-studio">
    <div className="diagnostic-title"><span>DIAGNOSTIC GUIDÉ 01</span><h2>Couverture d’équipements</h2><p>Mesurez les zones desservies, puis testez une implantation.</p></div>
    <label>Couche d’équipements<select value={sourceId} onChange={(event) => props.onSourceChange(event.target.value)}><option value="">Choisir une couche ponctuelle</option>{pointLayers.map((layer) => <option key={layer.id} value={layer.id}>{layer.name}</option>)}</select></label>
    <label>Rayon de couverture <b>{distance.toLocaleString("fr-FR")} m</b><input type="range" min="100" max="3000" step="100" value={distance} onChange={(event) => props.onDistanceChange(Number(event.target.value))} /></label>
    <div className="scenario-tools"><button className={placing ? "armed" : ""} onClick={props.onPlaceToggle}>{placing ? "Cliquez sur la carte…" : "+ Simuler un équipement"}</button>{scenarioLocations.length > 0 && <button className="clear" onClick={props.onClearScenario}>Effacer ({scenarioLocations.length})</button>}</div>
    <button className="run-diagnostic" disabled={!sourceId || running} onClick={props.onRun}>{running ? "Calcul du scénario…" : result ? "Recalculer le diagnostic" : "Lancer le diagnostic"}</button>
    {error && <p className="diagnostic-error">{error}</p>}
    {result && <>
      <div className="comparison-label"><span>SITUATION ACTUELLE</span><span>SCÉNARIO</span></div>
      <div className="coverage-comparison"><article><strong>{result.current.coverage_rate.toFixed(1)}%</strong><small>{result.current.covered_area_km2.toLocaleString("fr-FR")} km² couverts</small></article><i>→</i><article className="scenario"><strong>{result.scenario.coverage_rate.toFixed(1)}%</strong><small>{result.scenario.covered_area_km2.toLocaleString("fr-FR")} km² couverts</small></article></div>
      <div className="gain-card"><span>GAIN DU SCÉNARIO</span><strong>+{result.gain_points.toFixed(1)} points</strong><p>{result.interpretation}</p></div>
      <div className="coverage-bar"><i style={{ width: `${result.current.coverage_rate}%` }} /><b style={{ width: `${result.scenario.coverage_rate}%` }} /></div>
      <p className="method-warning">ⓘ {result.warnings[0]}</p>
      <button className="open-report" onClick={props.onOpenReport}>Composer le rapport décisionnel <b>→</b></button>
    </>}
  </section>;
}
