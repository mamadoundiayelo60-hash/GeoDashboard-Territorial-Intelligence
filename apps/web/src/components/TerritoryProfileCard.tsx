import type { TerritoryProfile } from "../api/territories";

const number = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });

export function TerritoryProfileCard({ territory }: { territory: TerritoryProfile }) {
  return <section className="territory-profile">
    <div className="territory-heading"><span>COMMUNE ACTIVE</span><h1>{territory.name}</h1><p>Code INSEE {territory.code} · Département {territory.department_code ?? "—"}</p></div>
    <div className="territory-metrics">
      <article><small>Population</small><strong>{territory.population?.toLocaleString("fr-FR") ?? "—"}</strong></article>
      <article><small>Superficie</small><strong>{number.format(territory.area_km2)} km²</strong></article>
      <article><small>Densité</small><strong>{territory.density_per_km2 ? `${number.format(territory.density_per_km2)} hab./km²` : "—"}</strong></article>
    </div>
    <p className="territory-source">Source : {territory.source}</p>
  </section>;
}
