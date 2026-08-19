import type { LayerSummary } from "../api/layers";

export function LayerInspector({ layer }: { layer: LayerSummary | null }) {
  if (!layer) return <div className="inspector-empty"><span>QUALITÉ & ATTRIBUTS</span><strong>Sélectionnez une couche</strong><p>Le profil de qualité et les premières valeurs seront examinés ici.</p></div>;
  const properties = layer.preview?.features[0]?.properties ?? {};
  const fields = Object.keys(properties);
  return <section className="layer-inspector">
    <div className="quality-header"><div><span>SCORE QUALITÉ</span><strong>{layer.quality.score}<small>/100</small></strong></div><i style={{ "--score": `${layer.quality.score}%` } as React.CSSProperties} /></div>
    <h2>{layer.name}</h2><p>{layer.source_format.toUpperCase()} · {layer.crs}</p>
    <div className="quality-grid"><article><strong>{layer.feature_count.toLocaleString("fr-FR")}</strong><small>Entités</small></article><article><strong>{layer.field_count}</strong><small>Champs</small></article></div>
    <ul className="quality-checks"><li><span>Géométries invalides</span><b>{layer.quality.invalid_geometries}</b></li><li><span>Géométries vides</span><b>{layer.quality.empty_geometries}</b></li><li><span>Doublons spatiaux</span><b>{layer.quality.duplicate_geometries}</b></li><li><span>Valeurs nulles</span><b>{layer.quality.null_cells}</b></li></ul>
    <div className="field-preview"><strong>Champs détectés</strong>{fields.length ? fields.slice(0, 8).map((field) => <div key={field}><span>{field}</span><code>{String(properties[field] ?? "—").slice(0, 28)}</code></div>) : <small>Aucun attribut métier</small>}</div>
  </section>;
}
