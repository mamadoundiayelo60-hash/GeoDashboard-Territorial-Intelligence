import { useEffect, useState } from "react";
import { createCalculatedField, executeSql, getHistory, type HistoryEvent, type SqlResult } from "../api/expert";
import type { LayerSummary } from "../api/layers";

type Tab = "field" | "sql" | "history";

export function ExpertWorkspace({ layers, onClose, onLayerUpdated }: { layers: LayerSummary[]; onClose: () => void; onLayerUpdated: () => void }) {
  const [tab, setTab] = useState<Tab>("field");
  const [layerId, setLayerId] = useState(layers[0]?.id ?? "");
  const [fieldName, setFieldName] = useState("");
  const [expression, setExpression] = useState("");
  const [sql, setSql] = useState("SELECT name, territory_code, created_at\nFROM geodashboard.v_projects");
  const [sqlResult, setSqlResult] = useState<SqlResult | null>(null);
  const [history, setHistory] = useState<HistoryEvent[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const refreshHistory = () => getHistory().then(setHistory).catch(() => undefined);
  useEffect(() => { void refreshHistory(); }, []);
  const calculate = async () => {
    setBusy(true); setError(null); setMessage(null);
    try { const result = await createCalculatedField(layerId, fieldName, expression); setMessage(`${result.field_name} créé · aperçu : ${result.preview.map(String).join(", ")}`); onLayerUpdated(); void refreshHistory(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Expression refusée."); }
    finally { setBusy(false); }
  };
  const runSql = async () => {
    setBusy(true); setError(null); setMessage(null);
    try { setSqlResult(await executeSql(sql)); void refreshHistory(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Requête refusée."); }
    finally { setBusy(false); }
  };
  return <section className="expert-workspace">
    <header><div><span>ATELIER EXPERT</span><h2>Données, expressions & PostGIS</h2></div><button onClick={onClose} aria-label="Fermer l’atelier">×</button></header>
    <nav><button className={tab === "field" ? "active" : ""} onClick={() => setTab("field")}>Champ calculé</button><button className={tab === "sql" ? "active" : ""} onClick={() => setTab("sql")}>SQL contrôlé</button><button className={tab === "history" ? "active" : ""} onClick={() => setTab("history")}>Historique <b>{history.length}</b></button></nav>
    <div className="expert-body">
      {tab === "field" && <div className="field-builder"><div className="expert-intro"><strong>Enrichir une couche sans code arbitraire</strong><p>Utilisez les champs existants, les opérateurs + − × ÷ et les fonctions autorisées : round, abs, upper, lower, length, coalesce.</p></div><label>Couche<select value={layerId} onChange={(event) => setLayerId(event.target.value)}>{layers.map((layer) => <option key={layer.id} value={layer.id}>{layer.name}</option>)}</select></label><label>Nouveau champ<input value={fieldName} onChange={(event) => setFieldName(event.target.value)} placeholder="densite_calculee" /></label><label className="expression-input">Expression<code>fx</code><input value={expression} onChange={(event) => setExpression(event.target.value)} placeholder="round(population / surface_km2, 1)" /></label><button className="expert-run" disabled={busy || !layerId || !fieldName || !expression} onClick={calculate}>Prévisualiser et créer</button></div>}
      {tab === "sql" && <div className="sql-console"><div className="sql-policy"><span>LECTURE SEULE</span><b>Vues geodashboard.v_* · 3 s · 200 lignes</b></div><textarea spellCheck={false} value={sql} onChange={(event) => setSql(event.target.value)} /><button className="expert-run" disabled={busy || !sql.trim()} onClick={runSql}>{busy ? "Exécution…" : "Exécuter la requête"}</button>{sqlResult && <div className="sql-result"><p>{sqlResult.row_count} lignes · {sqlResult.duration_ms} ms{sqlResult.truncated ? " · résultat tronqué" : ""}</p><div><table><thead><tr>{sqlResult.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{sqlResult.rows.map((row, rowIndex) => <tr key={rowIndex}>{row.map((value, index) => <td key={index}>{String(value ?? "—")}</td>)}</tr>)}</tbody></table></div></div>}</div>}
      {tab === "history" && <div className="history-list">{history.map((event) => <article key={event.id}><i /><div><strong>{event.summary}</strong><small>{new Date(event.created_at).toLocaleString("fr-FR")} · {event.event_type}</small></div></article>)}{!history.length && <p>Aucune transformation n’a encore été enregistrée.</p>}</div>}
      {message && <p className="expert-message">✓ {message}</p>}{error && <p className="expert-error">{error}</p>}
    </div>
  </section>;
}
