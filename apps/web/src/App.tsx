import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  downloadDecisionReport,
  runSiteSelection,
  type DecisionWeights,
} from "./api/decisions";
import { getTerritory, type CommuneSummary } from "./api/territories";
import {
  DecisionMap,
  type DecisionLayerId,
  type DecisionLayerVisibility,
} from "./components/DecisionMap";
import { TerritorySearch } from "./components/TerritorySearch";
import { uploadLayer, type LayerSummary } from "./api/layers";

const format = new Intl.NumberFormat("fr-FR");
type ThemeId = "health" | "education" | "sport" | "culture";
type Workspace = "observe" | "decide" | "compare" | "report";
const themes: Record<ThemeId, { label: string; eyebrow: string; title: string; description: string }> = {
  health: { label: "Santé", eyebrow: "ACCÈS AUX SOINS", title: "Où implanter le prochain service de santé ?", description: "Réduire les déserts de soins en priorisant les secteurs vulnérables." },
  education: { label: "Éducation", eyebrow: "ACCÈS À L’ÉDUCATION", title: "Où renforcer l’offre éducative ?", description: "Identifier les secteurs éloignés des équipements d’apprentissage." },
  sport: { label: "Sport", eyebrow: "ACCÈS AU SPORT", title: "Où créer le prochain équipement sportif ?", description: "Rééquilibrer l’accès aux équipements sportifs de proximité." },
  culture: { label: "Culture", eyebrow: "ACCÈS À LA CULTURE", title: "Où développer l’offre culturelle ?", description: "Repérer les quartiers sous-dotés en services culturels de proximité." },
};
const layerDefinitions: Array<{
  id: DecisionLayerId;
  label: string;
  detail: string;
  color: string;
}> = [
  {
    id: "facilities",
    label: "Équipements existants",
    detail: "Santé · OpenStreetMap",
    color: "#f8fafc",
  },
  {
    id: "grid",
    label: "Population & vulnérabilité",
    detail: "INSEE Filosofi 2021 · 200 m",
    color: "#ff5c7a",
  },
  {
    id: "currentArea",
    label: "Accessibilité actuelle",
    detail: "Seuil sélectionné",
    color: "#55d7cf",
  },
  {
    id: "scenarioArea",
    label: "Impact du scénario",
    detail: "Avec le site A",
    color: "#6cf3c5",
  },
  {
    id: "candidates",
    label: "Parcelles préqualifiées",
    detail: "Cadastre · zones U/AU · hors eau",
    color: "#ffd166",
  },
];

export function App() {
  const [workspace, setWorkspace] = useState<Workspace>("decide");
  const [theme, setTheme] = useState<ThemeId>("health");
  const [equipmentLayer, setEquipmentLayer] = useState<LayerSummary | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const uploadInput = useRef<HTMLInputElement | null>(null);
  const [selected, setSelected] = useState<CommuneSummary>({
    code: "62193",
    name: "Calais",
    department_code: "62",
    region_code: "32",
    postal_codes: ["62100"],
    population: 67544,
  });
  const [searchOpen, setSearchOpen] = useState(false);
  const [catalogOpen, setCatalogOpen] = useState(true);
  const [mode, setMode] = useState("pedestrian");
  const [minutes, setMinutes] = useState(15);
  const [comparison, setComparison] = useState(100);
  const [reporting, setReporting] = useState(false);
  const [weights, setWeights] = useState<DecisionWeights>({
    population: 0.45,
    vulnerability: 0.35,
    equity: 0.2,
  });
  const [question, setQuestion] = useState(
    "Pourquoi le site A est-il recommandé ?",
  );
  const [visibility, setVisibility] = useState<DecisionLayerVisibility>({
    grid: true,
    currentArea: true,
    scenarioArea: true,
    facilities: true,
    candidates: true,
  });
  const territory = useQuery({
    queryKey: ["territory", selected.code],
    queryFn: () => getTerritory(selected.code),
  });
  const isPilotTerritory = selected.code === "62193";
  const study = useMutation({
    mutationFn: () =>
      runSiteSelection({
        territoryGeometry: territory.data!.geometry,
        territoryName: territory.data!.name,
        territoryCode: territory.data!.code,
        population: territory.data!.population ?? 1,
        theme,
        mode,
        thresholdMinutes: minutes,
        weights,
        equipmentLayerId: equipmentLayer?.id,
      }),
  });
  useEffect(() => {
    study.reset();
    if (territory.data && isPilotTerritory) study.mutate();
  }, [territory.data, isPilotTerritory, theme, equipmentLayer]);
  const result = study.isError ? null : (study.data ?? null);
  const topCandidates = useMemo(
    () => result?.candidates.features.slice(0, 3) ?? [],
    [result],
  );
  const setWeight = (key: keyof DecisionWeights, value: number) =>
    setWeights((current) => ({ ...current, [key]: value }));
  const toggleLayer = (id: DecisionLayerId) =>
    setVisibility((current) => ({ ...current, [id]: !current[id] }));

  return (
    <div className="v2-app">
      <header className="v2-header">
        <div className="brand">
          <i>TS</i>
          <div>
            <strong>
              TerriScope <em>AI</em>
            </strong>
            <span>SPATIAL DECISION INTELLIGENCE</span>
          </div>
        </div>
        <nav>{(["observe", "decide", "compare", "report"] as Workspace[]).map((item) => (
          <button className={workspace === item ? "active" : ""} onClick={() => setWorkspace(item)} key={item}>
            {{ observe: "Observer", decide: "Décider", compare: "Comparer", report: "Restituer" }[item]}
          </button>
        ))}</nav>
        <button onClick={() => setSearchOpen(!searchOpen)}>
          ⌖ {selected.name} · {selected.code}
        </button>
      </header>
      {searchOpen && (
        <div className="territory-popover">
          <TerritorySearch
            onSelect={(value) => {
              setSelected(value);
              setSearchOpen(false);
            }}
          />
        </div>
      )}
      <main className="v2-main">
        <aside className="decision-panel">
          <div className="eyebrow">ÉTUDE 01 · {themes[theme].eyebrow}</div>
          <h1>{workspace === "observe" ? `Observer l’offre ${themes[theme].label.toLowerCase()}` : workspace === "compare" ? "Comparer les scénarios" : workspace === "report" ? "Restituer la décision" : themes[theme].title}</h1>
          <p>{workspace === "observe" ? "Explorez l’offre existante, la demande et les secteurs non desservis." : workspace === "compare" ? "Comparez les alternatives avec des indicateurs homogènes et explicables." : workspace === "report" ? "Produisez une note professionnelle avec méthode, sources et limites." : themes[theme].description}</p>
          <section><label>THÉMATIQUE TERRITORIALE</label><div className="theme-switch">
            {(Object.keys(themes) as ThemeId[]).map((id) => <button className={theme === id ? "active" : ""} onClick={() => { setTheme(id); setEquipmentLayer(null); setUploadError(null); }} key={id}>{themes[id].label}</button>)}
          </div></section>
          <section className="equipment-import">
            <label>DONNÉES MÉTIER</label>
            <input ref={uploadInput} hidden type="file" accept=".geojson,.json,.gpkg,.zip,.kml,.csv" onChange={(event) => {
              const file = event.target.files?.[0]; if (!file) return;
              setUploading(true); setUploadError(null);
              void uploadLayer(file).then(setEquipmentLayer).catch((error: Error) => setUploadError(error.message)).finally(() => { setUploading(false); event.target.value = ""; });
            }} />
            <button className="import-action" disabled={uploading} onClick={() => uploadInput.current?.click()}>{uploading ? "Contrôle de la couche…" : "+ Importer mes équipements"}</button>
            {equipmentLayer ? <div className="import-success"><b>{equipmentLayer.name}</b><span>{equipmentLayer.feature_count} points · qualité {equipmentLayer.quality.score}/100</span><button onClick={() => setEquipmentLayer(null)}>Utiliser OSM</button></div> : <small>GeoJSON, GeoPackage, Shapefile ZIP, KML ou CSV géographique.</small>}
            {uploadError && <small className="error">{uploadError}</small>}
          </section>
          <section>
            <label>MODE DE DÉPLACEMENT</label>
            <div className="mode-switch">
              {[
                ["pedestrian", "À pied"],
                ["bicycle", "Vélo"],
                ["car", "Voiture"],
              ].map(([id, label]) => (
                <button
                  className={mode === id ? "active" : ""}
                  onClick={() => setMode(id)}
                  key={id}
                >
                  {label}
                </button>
              ))}
            </div>
          </section>
          <section>
            <label>
              SEUIL D’ACCÈS <b>{minutes} min</b>
            </label>
            <input
              type="range"
              min="5"
              max="30"
              step="5"
              value={minutes}
              onChange={(event) => setMinutes(Number(event.target.value))}
            />
          </section>
          <section className="weights">
            <label>PRIORITÉS DU MODÈLE</label>
            {[
              ["population", "Population"],
              ["vulnerability", "Vulnérabilité"],
              ["equity", "Équité spatiale"],
            ].map(([key, label]) => (
              <div key={key}>
                <span>{label}</span>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step=".05"
                  value={weights[key as keyof DecisionWeights]}
                  onChange={(event) =>
                    setWeight(
                      key as keyof DecisionWeights,
                      Number(event.target.value),
                    )
                  }
                />
                <b>
                  {Math.round(weights[key as keyof DecisionWeights] * 100)}%
                </b>
              </div>
            ))}
          </section>
          <button
            className="primary"
            disabled={!territory.data || !isPilotTerritory || study.isPending}
            onClick={() => study.mutate()}
          >
            {study.isPending
              ? "Analyse spatiale en cours…"
              : isPilotTerritory
                ? "Recalculer les recommandations"
                : "Territoire à préparer"}
          </button>
          {!isPilotTerritory && (
            <small className="territory-notice">
              ● La limite communale peut être explorée. Le diagnostic nécessite
              encore les équipements, la population carroyée et les contraintes
              d’implantation de ce territoire.
            </small>
          )}
          {study.error && (
            <small className="error">{study.error.message}</small>
          )}
          {result && (
            <small className="data-status">● {result.data_status}</small>
          )}
        </aside>
        <section className="map-stage">
          {territory.data && (
            <DecisionMap
              territory={territory.data}
              result={result}
              comparison={comparison}
              visibility={visibility}
              facilityLabel={`Équipement — ${themes[theme].label}`}
            />
          )}
          <button
            className="catalog-trigger"
            onClick={() => setCatalogOpen(!catalogOpen)}
          >
            ◫ Couches{" "}
            <b>
              {isPilotTerritory
                ? Object.values(visibility).filter(Boolean).length
                : 0}
            </b>
          </button>
          {catalogOpen && (
            <div className="map-catalog">
              <header>
                <div>
                  <span>CATALOGUE CARTOGRAPHIQUE</span>
                  <strong>
                    {isPilotTerritory
                      ? "Données de l’étude"
                      : "Socle métier non chargé"}
                  </strong>
                </div>
                <button onClick={() => setCatalogOpen(false)}>×</button>
              </header>
              {layerDefinitions.map((layer) => (
                <button
                  disabled={!isPilotTerritory}
                  className={
                    isPilotTerritory && visibility[layer.id] ? "visible" : ""
                  }
                  key={layer.id}
                  onClick={() => toggleLayer(layer.id)}
                >
                  <i style={{ background: layer.color }} />
                  <div>
                    <strong>{layer.label}</strong>
                    <small>{layer.id === "facilities" ? `${themes[theme].label} · OpenStreetMap` : layer.detail}</small>
                  </div>
                  <b>{isPilotTerritory && visibility[layer.id] ? "ON" : "—"}</b>
                </button>
              ))}
              <p>
                {isPilotTerritory
                  ? "Cliquez sur un équipement, une maille ou un candidat pour consulter sa fiche."
                  : "La limite communale est disponible. Les couches décisionnelles seront activées après préparation des sources locales."}
              </p>
            </div>
          )}
          {isPilotTerritory && result?.has_actionable_gain && (
            <div className="compare-control">
              <span>Situation actuelle</span>
              <input
                type="range"
                min="0"
                max="100"
                value={comparison}
                onChange={(event) => setComparison(Number(event.target.value))}
              />
              <span>Avec site A</span>
            </div>
          )}
        </section>
        <aside className="insight-panel">
          <div className="eyebrow">IMPACT DU MEILLEUR SCÉNARIO</div>
          {result && workspace === "observe" ? (
            <div className="workspace-summary">
              <b>PORTRAIT TERRITORIAL</b><strong>{themes[theme].label} · {selected.name}</strong>
              <article><span>Équipements observés</span><strong>{result.facilities.features.length}</strong></article>
              <article><span>Population accessible</span><strong>{result.current_access_rate}%</strong></article>
              <article><span>Habitants encore éloignés</span><strong>{format.format(result.underserved_people)}</strong></article>
              <p>Cette vue décrit l’existant. Passez à « Décider » pour simuler une implantation.</p>
            </div>
          ) : result && workspace === "compare" ? (
            <div className="workspace-summary">
              <b>COMPARAISON MULTICRITÈRE</b><strong>{topCandidates.length ? `${topCandidates.length} alternatives` : "Aucune alternative utile"}</strong>
              {topCandidates.map((feature, index) => <article key={index}><span>Parcelle {String.fromCharCode(65 + index)}</span><strong>{String(feature.properties?.score)}/100 · +{format.format(Number(feature.properties?.gained_people ?? 0))}</strong></article>)}
              <p>Le score est relatif à cette étude et ne remplace pas l’instruction foncière ou réglementaire.</p>
            </div>
          ) : result && workspace === "report" ? (
            <div className="workspace-summary"><b>RESTITUTION</b><strong>Note décisionnelle prête</strong><p>Territoire, paramètres, carte, recommandation, sources et limites sont réunis dans un PDF professionnel.</p>
              <button className="report" disabled={reporting} onClick={() => { if (!territory.data) return; setReporting(true); void downloadDecisionReport({ territory: territory.data, decision: result, mode, thresholdMinutes: minutes, weights }).finally(() => setReporting(false)); }}>{reporting ? "Génération du PDF…" : "Télécharger la note décisionnelle ↗"}</button>
            </div>
          ) : result ? (
            <>
              {!result.has_actionable_gain && <div className="no-gain"><b>AUCUNE IMPLANTATION PRIORITAIRE</b><strong>Le scénario n’améliore pas l’accès</strong><p>{result.decision_message}</p></div>}
              {result.has_actionable_gain && <>
              <div className="hero-metric">
                <span>Habitants supplémentaires accessibles</span>
                <strong>+{format.format(result.gained_people)}</strong>
                <small>dans le seuil de {minutes} minutes</small>
              </div>
              <div className="kpi-row">
                <article>
                  <span>Actuel</span>
                  <b>{result.current_access_rate}%</b>
                </article>
                <i>→</i>
                <article className="after">
                  <span>Scénario</span>
                  <b>{result.scenario_access_rate}%</b>
                </article>
              </div>
              <div className="recommend">
                <span>RECOMMANDATION N°1</span>
                <strong>
                  Parcelle A · score relatif {result.recommendation.score}/100
                </strong>
                <p>{result.recommendation.explanation}</p>
              </div>
              <div className="ranking">
                <label>ALTERNATIVES</label>
                {topCandidates.map((feature, index) => (
                  <article key={index}>
                    <b>{String.fromCharCode(65 + index)}</b>
                    <div>
                      <strong>
                        Parcelle candidate {String.fromCharCode(65 + index)}
                      </strong>
                      <small>
                        +
                        {format.format(
                          Number(feature.properties?.gained_people ?? 0),
                        )}{" "}
                        habitants
                      </small>
                    </div>
                    <em>{String(feature.properties?.score)}/100</em>
                  </article>
                ))}
              </div>
              <div className="ai-card">
                <span>ASSISTANT EXPLICABLE</span>
                <strong>Interroger l’étude</strong>
                <div>
                  {[
                    "Pourquoi cette zone ?",
                    "Qui en bénéficie ?",
                    "Quelles limites ?",
                  ].map((item) => (
                    <button key={item} onClick={() => setQuestion(item)}>
                      {item}
                    </button>
                  ))}
                </div>
                <p>
                  <b>Question :</b> {question}
                </p>
                <p>
                  {question.includes("limites")
                    ? result.limitations[0]
                    : result.recommendation.explanation}{" "}
                  <u>Sources vérifiables</u>
                </p>
              </div>
              <button
                className="report"
                disabled={reporting}
                onClick={() => {
                  if (!territory.data) return;
                  setReporting(true);
                  void downloadDecisionReport({
                    territory: territory.data,
                    decision: result,
                    mode,
                    thresholdMinutes: minutes,
                    weights,
                  }).finally(() => setReporting(false));
                }}
              >
                {reporting ? "Génération du PDF…" : "Télécharger la note décisionnelle ↗"}
              </button>
              </>}
            </>
          ) : !isPilotTerritory ? (
            <div className="territory-empty">
              <b>Territoire exploratoire</b>
              <strong>{selected.name}</strong>
              <p>
                Aucun scénario n’est calculé sans données locales vérifiées.
              </p>
              <ul>
                <li>Équipements métier</li>
                <li>Population carroyée</li>
                <li>Contraintes eau, foncier et urbanisme</li>
              </ul>
              <small>Territoire pilote disponible : Calais · 62193</small>
            </div>
          ) : (
            <div className="skeleton">
              Construction du diagnostic territorial…
            </div>
          )}
        </aside>
      </main>
      <footer>
        <span>Méthode : {result?.method ?? "chargement"}</span>
        <span>
          {result?.sources.map((source) => source.provider).join(" · ")}
        </span>
      </footer>
    </div>
  );
}
