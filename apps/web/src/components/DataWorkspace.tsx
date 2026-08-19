import { useRef, useState } from "react";
import type { LayerSummary } from "../api/layers";
import { layerColor } from "../utils/layerColors";

type Props = {
  layers: LayerSummary[];
  visibleIds: Set<string>;
  selectedId: string | null;
  uploading: boolean;
  error: string | null;
  onUpload: (file: File, crs?: string) => void;
  onToggle: (id: string) => void;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onOpenExpert: () => void;
  onLoadDemo: () => void;
};

export function DataWorkspace({ layers, visibleIds, selectedId, uploading, error, onUpload, onToggle, onSelect, onDelete, onOpenExpert, onLoadDemo }: Props) {
  const input = useRef<HTMLInputElement | null>(null);
  const [crs, setCrs] = useState("");
  const accept = ".geojson,.json,.gpkg,.zip,.kml,.csv";
  const choose = (file?: File) => file && onUpload(file, crs.trim() || undefined);
  return <>
    <section className="import-card">
      <div><span>AJOUTER UNE SOURCE</span><strong>Déposez une donnée métier</strong><small>GeoJSON · GPKG · Shapefile ZIP · KML · CSV</small></div>
      <input ref={input} hidden type="file" accept={accept} onChange={(event) => choose(event.target.files?.[0])} />
      <button disabled={uploading} onClick={() => input.current?.click()}>{uploading ? "Contrôle en cours…" : "+ Importer"}</button>
      <button className="demo-action" disabled={uploading} onClick={onLoadDemo}>▶ Charger la démo Calais</button>
      <label>CRS source si absent<input value={crs} onChange={(event) => setCrs(event.target.value)} placeholder="ex. EPSG:2154" /></label>
      {error && <p className="data-error">{error}</p>}
      <p className="demo-source">103 équipements · OpenStreetMap · ODbL 1.0</p>
    </section>
    <div className="catalog-heading"><strong>Catalogue</strong><span>{layers.length} couche{layers.length > 1 ? "s" : ""}</span></div>
    <div className="layer-catalog">
      {layers.map((layer, index) => <article className={selectedId === layer.id ? "selected" : ""} key={layer.id} onClick={() => onSelect(layer.id)}>
        <button className={`visibility ${visibleIds.has(layer.id) ? "on" : ""}`} title="Afficher/masquer" onClick={(event) => { event.stopPropagation(); onToggle(layer.id); }} aria-label={`Afficher ${layer.name}`}>●</button>
        <div><strong>{layer.name}</strong><small>{layer.feature_count.toLocaleString("fr-FR")} objets · {layer.geometry_types.join(", ")}</small></div>
        <span className={`quality-score ${layer.quality.score >= 80 ? "good" : layer.quality.score >= 60 ? "medium" : "bad"}`}>{layer.quality.score}</span>
        <button className="delete-layer" title="Supprimer" onClick={(event) => { event.stopPropagation(); onDelete(layer.id); }}>×</button>
        <i style={{ background: layerColor(index) }} />
      </article>)}
      {!layers.length && <p className="catalog-empty">Votre catalogue est vide. Importez une couche pour enrichir le diagnostic.</p>}
    </div>
    {layers.length > 0 && <button className="open-expert" onClick={onOpenExpert}><span>⌘</span><div><strong>Ouvrir l’atelier expert</strong><small>Expressions · SQL · historique</small></div><b>→</b></button>}
  </>;
}
