#!/usr/bin/env python3
"""Extrait un territoire depuis Filosofi 200 m et produit un GeoJSON web léger."""

import argparse
import csv
import json
import re
from pathlib import Path
from zipfile import ZipFile

from pyproj import Transformer
from shapely.geometry import box, mapping
from shapely.ops import transform

CELL_PATTERN = re.compile(r"CRS3035RES200mN(?P<north>\d+)E(?P<east>\d+)")
COMPONENT_WEIGHTS = {
    "poverty_rate": 0.40,
    "senior_rate": 0.30,
    "single_parent_rate": 0.15,
    "social_housing_rate": 0.15,
}


def _ratio(numerator: str, denominator: str) -> float:
    value = float(numerator or 0)
    total = float(denominator or 0)
    return value / total if total > 0 else 0.0


def _normalize(rows: list[dict[str, object]], field: str) -> None:
    values = [float(row[field]) for row in rows]
    low, high = min(values), max(values)
    for row in rows:
        row[f"{field}_norm"] = (
            (float(row[field]) - low) / (high - low) if high > low else 0.0
        )


def extract_filosofi(zip_path: Path, commune_code: str) -> list[dict[str, object]]:
    """Lit le CSV national en flux et conserve les carreaux rattachés à une commune."""
    rows: list[dict[str, object]] = []
    locality_codes = (
        {f"751{index:02d}" for index in range(1, 21)}
        if commune_code == "75056"
        else {commune_code}
    )
    with ZipFile(zip_path) as archive, archive.open("carreaux_200m_met.csv") as raw:
        reader = csv.DictReader(line.decode("utf-8") for line in raw)
        for source in reader:
            if not any(code in source["lcog_geo"] for code in locality_codes):
                continue
            identifier = source["idcar_200m"]
            match = CELL_PATTERN.fullmatch(identifier)
            if not match:
                raise ValueError(f"Identifiant de carreau invalide : {identifier}")
            population = float(source["ind"] or 0)
            households = float(source["men"] or 0)
            rows.append(
                {
                    "id": identifier,
                    "north": int(match.group("north")),
                    "east": int(match.group("east")),
                    "population": population,
                    "households": households,
                    "poverty_rate": _ratio(source["men_pauv"], source["men"]),
                    "senior_rate": (
                        float(source["ind_65_79"] or 0) + float(source["ind_80p"] or 0)
                    )
                    / population
                    if population > 0
                    else 0.0,
                    "single_parent_rate": _ratio(source["men_fmp"], source["men"]),
                    "social_housing_rate": _ratio(source["log_soc"], source["men"]),
                    "imputed": source["i_est_200"] == "1",
                }
            )
    if not rows:
        raise ValueError(f"Aucun carreau Filosofi trouvé pour {commune_code}.")
    for component in COMPONENT_WEIGHTS:
        _normalize(rows, component)
    for row in rows:
        row["vulnerability"] = round(
            100
            * sum(
                float(row[f"{component}_norm"]) * weight
                for component, weight in COMPONENT_WEIGHTS.items()
            ),
            1,
        )
    return rows


def to_geojson(rows: list[dict[str, object]], commune_code: str) -> dict[str, object]:
    """Reconstruit les carrés LAEA de 200 m et les reprojette en WGS84."""
    transformer = Transformer.from_crs(3035, 4326, always_xy=True)
    features = []
    for row in rows:
        east, north = int(row["east"]), int(row["north"])
        geometry = transform(
            transformer.transform, box(east, north, east + 200, north + 200)
        )
        properties = {
            key: value
            for key, value in row.items()
            if key not in {"north", "east"} and not key.endswith("_norm")
        }
        features.append(
            {"type": "Feature", "geometry": mapping(geometry), "properties": properties}
        )
    return {
        "type": "FeatureCollection",
        "name": f"Filosofi 2021 — commune {commune_code}",
        "metadata": {
            "source": "INSEE — Filosofi 2021, carreaux de 200 m",
            "published": "2026-02-12",
            "crs": "EPSG:4326",
            "vulnerability_formula": COMPONENT_WEIGHTS,
        },
        "features": features,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--commune", default="62193")
    args = parser.parse_args()
    data = to_geojson(extract_filosofi(args.zip_path, args.commune), args.commune)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    population = sum(
        float(feature["properties"]["population"]) for feature in data["features"]
    )
    imputed = sum(
        bool(feature["properties"]["imputed"]) for feature in data["features"]
    )
    print(
        f"{len(data['features'])} carreaux, {population:.0f} habitants, {imputed} imputés"
    )


if __name__ == "__main__":
    main()
