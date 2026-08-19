import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { searchCommunes, type CommuneSummary } from "../api/territories";

export function TerritorySearch({ onSelect }: { onSelect: (commune: CommuneSummary) => void }) {
  const [input, setInput] = useState("");
  const [submitted, setSubmitted] = useState("");
  const search = useQuery({ queryKey: ["communes", submitted], queryFn: () => searchCommunes(submitted), enabled: submitted.length >= 2 });

  return (
    <section className="territory-search" aria-label="Recherche territoriale">
      <form onSubmit={(event) => { event.preventDefault(); const value = input.trim(); if (value.length >= 2) setSubmitted(value); }}>
        <label htmlFor="commune-search">Commune, code postal ou code INSEE</label>
        <div><input id="commune-search" value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ex. Calais, 62100 ou 62193" maxLength={80} autoComplete="off" /><button type="submit">Rechercher</button></div>
      </form>
      {search.isFetching && <p className="search-status">Recherche du territoire…</p>}
      {search.isError && <p className="search-error">{search.error.message}</p>}
      {search.data && submitted && <div className="search-results">
        {search.data.length === 0 && <p>Aucune commune trouvée.</p>}
        {search.data.map((commune) => <button key={commune.code} onClick={() => onSelect(commune)}><span><strong>{commune.name}</strong><small>Département {commune.department_code ?? "—"} · {commune.postal_codes.join(", ")}</small></span><b>{commune.code}</b></button>)}
      </div>}
    </section>
  );
}
