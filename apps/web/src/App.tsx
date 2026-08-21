import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { runSiteSelection, type DecisionWeights } from "./api/decisions";
import { getTerritory, type CommuneSummary } from "./api/territories";
import { DecisionMap, type DecisionLayerId, type DecisionLayerVisibility } from "./components/DecisionMap";
import { TerritorySearch } from "./components/TerritorySearch";

const format = new Intl.NumberFormat("fr-FR");
const layerDefinitions: Array<{ id: DecisionLayerId; label: string; detail: string; color: string }> = [
  { id: "facilities", label: "Équipements existants", detail: "Santé · OpenStreetMap", color: "#f8fafc" },
  { id: "grid", label: "Population & vulnérabilité", detail: "INSEE Filosofi 2021 · 200 m", color: "#ff5c7a" },
  { id: "currentArea", label: "Accessibilité actuelle", detail: "Seuil sélectionné", color: "#55d7cf" },
  { id: "scenarioArea", label: "Impact du scénario", detail: "Avec le site A", color: "#6cf3c5" },
  { id: "candidates", label: "Sites candidats", detail: "Classement multicritère", color: "#ffd166" },
];

export function App() {
  const [selected, setSelected] = useState<CommuneSummary>({ code: "62193", name: "Calais", department_code: "62", region_code: "32", postal_codes: ["62100"], population: 67544 });
  const [searchOpen, setSearchOpen] = useState(false);
  const [catalogOpen, setCatalogOpen] = useState(true);
  const [mode, setMode] = useState("pedestrian");
  const [minutes, setMinutes] = useState(15);
  const [comparison, setComparison] = useState(100);
  const [weights, setWeights] = useState<DecisionWeights>({ population: .45, vulnerability: .35, equity: .20 });
  const [question, setQuestion] = useState("Pourquoi le site A est-il recommandé ?");
  const [visibility, setVisibility] = useState<DecisionLayerVisibility>({ grid: true, currentArea: true, scenarioArea: true, facilities: true, candidates: true });
  const territory = useQuery({ queryKey: ["territory", selected.code], queryFn: () => getTerritory(selected.code) });
  const study = useMutation({ mutationFn: () => runSiteSelection({ territoryGeometry: territory.data!.geometry, territoryName: territory.data!.name, territoryCode: territory.data!.code, population: territory.data!.population ?? 1, mode, thresholdMinutes: minutes, weights }) });
  useEffect(() => { if (territory.data) study.mutate(); }, [territory.data]);
  const result = study.data ?? null;
  const topCandidates = useMemo(() => result?.candidates.features.slice(0, 3) ?? [], [result]);
  const setWeight = (key: keyof DecisionWeights, value: number) => setWeights(current => ({ ...current, [key]: value }));
  const toggleLayer = (id: DecisionLayerId) => setVisibility(current => ({ ...current, [id]: !current[id] }));

  return <div className="v2-app">
    <header className="v2-header"><div className="brand"><i>TS</i><div><strong>TerriScope <em>AI</em></strong><span>SPATIAL DECISION INTELLIGENCE</span></div></div><nav><b>Observer</b><b className="active">Décider</b><b>Comparer</b><b>Restituer</b></nav><button onClick={() => setSearchOpen(!searchOpen)}>⌖ {selected.name} · {selected.code}</button></header>
    {searchOpen && <div className="territory-popover"><TerritorySearch onSelect={value => { setSelected(value); setSearchOpen(false); }} /></div>}
    <main className="v2-main">
      <aside className="decision-panel"><div className="eyebrow">ÉTUDE 01 · ACCÈS AUX SOINS</div><h1>Où implanter le prochain service de santé&nbsp;?</h1><p>Réduire le nombre d’habitants éloignés d’un équipement, en priorisant les secteurs vulnérables.</p>
        <section><label>MODE DE DÉPLACEMENT</label><div className="mode-switch">{[["pedestrian", "À pied"], ["bicycle", "Vélo"], ["car", "Voiture"]].map(([id, label]) => <button className={mode === id ? "active" : ""} onClick={() => setMode(id)} key={id}>{label}</button>)}</div></section>
        <section><label>SEUIL D’ACCÈS <b>{minutes} min</b></label><input type="range" min="5" max="30" step="5" value={minutes} onChange={event => setMinutes(Number(event.target.value))} /></section>
        <section className="weights"><label>PRIORITÉS DU MODÈLE</label>{[["population", "Population"], ["vulnerability", "Vulnérabilité"], ["equity", "Équité spatiale"]].map(([key, label]) => <div key={key}><span>{label}</span><input type="range" min="0" max="1" step=".05" value={weights[key as keyof DecisionWeights]} onChange={event => setWeight(key as keyof DecisionWeights, Number(event.target.value))} /><b>{Math.round(weights[key as keyof DecisionWeights] * 100)}%</b></div>)}</section>
        <button className="primary" disabled={!territory.data || study.isPending} onClick={() => study.mutate()}>{study.isPending ? "Analyse spatiale en cours…" : "Recalculer les recommandations"}</button>{study.error && <small className="error">{study.error.message}</small>}{result && <small className="data-status">● {result.data_status}</small>}
      </aside>
      <section className="map-stage">
        {territory.data && <DecisionMap territory={territory.data} result={result} comparison={comparison} visibility={visibility} />}
        <button className="catalog-trigger" onClick={() => setCatalogOpen(!catalogOpen)}>◫ Couches <b>{Object.values(visibility).filter(Boolean).length}</b></button>
        {catalogOpen && <div className="map-catalog"><header><div><span>CATALOGUE CARTOGRAPHIQUE</span><strong>Données de l’étude</strong></div><button onClick={() => setCatalogOpen(false)}>×</button></header>{layerDefinitions.map(layer => <button className={visibility[layer.id] ? "visible" : ""} key={layer.id} onClick={() => toggleLayer(layer.id)}><i style={{ background: layer.color }} /><div><strong>{layer.label}</strong><small>{layer.detail}</small></div><b>{visibility[layer.id] ? "ON" : "OFF"}</b></button>)}<p>Cliquez sur un équipement, une maille ou un candidat pour consulter sa fiche.</p></div>}
        <div className="compare-control"><span>Situation actuelle</span><input type="range" min="0" max="100" value={comparison} onChange={event => setComparison(Number(event.target.value))} /><span>Avec site A</span></div>
      </section>
      <aside className="insight-panel"><div className="eyebrow">IMPACT DU MEILLEUR SCÉNARIO</div>{result ? <><div className="hero-metric"><span>Habitants supplémentaires accessibles</span><strong>+{format.format(result.gained_people)}</strong><small>dans le seuil de {minutes} minutes</small></div><div className="kpi-row"><article><span>Actuel</span><b>{result.current_access_rate}%</b></article><i>→</i><article className="after"><span>Scénario</span><b>{result.scenario_access_rate}%</b></article></div><div className="recommend"><span>RECOMMANDATION N°1</span><strong>Site A · score relatif {result.recommendation.score}/100</strong><p>{result.recommendation.explanation}</p></div><div className="ranking"><label>ALTERNATIVES</label>{topCandidates.map((feature, index) => <article key={index}><b>{String.fromCharCode(65 + index)}</b><div><strong>Site candidat {String.fromCharCode(65 + index)}</strong><small>+{format.format(Number(feature.properties?.gained_people ?? 0))} habitants</small></div><em>{String(feature.properties?.score)}/100</em></article>)}</div><div className="ai-card"><span>ASSISTANT EXPLICABLE</span><strong>Interroger l’étude</strong><div>{["Pourquoi ce site ?", "Qui en bénéficie ?", "Quelles limites ?"].map(item => <button key={item} onClick={() => setQuestion(item)}>{item}</button>)}</div><p><b>Question :</b> {question}</p><p>{question.includes("limites") ? result.limitations[0] : result.recommendation.explanation} <u>Sources vérifiables</u></p></div><button className="report" onClick={() => window.print()}>Générer la note décisionnelle ↗</button></> : <div className="skeleton">Construction du diagnostic territorial…</div>}</aside>
    </main>
    <footer><span>Méthode : {result?.method ?? "chargement"}</span><span>{result?.sources.map(source => source.provider).join(" · ")}</span></footer>
  </div>;
}

