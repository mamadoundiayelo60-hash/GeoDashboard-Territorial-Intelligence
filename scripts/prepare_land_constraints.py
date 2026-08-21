#!/usr/bin/env python3
"""Prépare les parcelles candidates de Calais à partir du GPU et du cadastre."""

import argparse
import gzip
import json
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree


def _read(path: Path) -> dict[str, object]:
    if path.suffix == ".gz":
        stream = gzip.open(path, "rt", encoding="utf-8")
    else:
        stream = path.open("rt", encoding="utf-8")
    with stream:
        return json.load(stream)


def build_candidates(
    gpu_payload: dict[str, object],
    parcel_payload: dict[str, object],
    water_payload: dict[str, object],
    demand_payload: dict[str, object] | None = None,
    minimum_area: float = 500,
    maximum_area: float = 50_000,
) -> dict[str, object]:
    """Conserve les parcelles de taille utile situées en zone U/AU et hors eau."""
    allowed_features = [
        feature
        for feature in gpu_payload.get("features", [])
        if str(feature.get("properties", {}).get("typezone", "")).startswith(("U", "AU"))
    ]
    allowed_geometries = [shape(feature["geometry"]) for feature in allowed_features]
    if not allowed_geometries:
        raise ValueError("Aucune zone urbaine ou à urbaniser n'a été trouvée dans le GPU.")
    allowed_tree = STRtree(allowed_geometries)
    water = unary_union(
        [shape(feature["geometry"]) for feature in water_payload.get("features", [])]
    )
    to_metric = Transformer.from_crs(4326, 2154, always_xy=True).transform

    candidates = []
    for feature in parcel_payload.get("features", []):
        parcel = shape(feature["geometry"])
        if parcel.is_empty or not parcel.is_valid:
            continue
        area = transform(to_metric, parcel).area
        if not minimum_area <= area <= maximum_area:
            continue
        center = parcel.representative_point()
        if water.covers(center):
            continue
        matches = allowed_tree.query(center, predicate="within")
        if not len(matches):
            continue
        zone = allowed_features[int(matches[0])]["properties"]
        properties = feature.get("properties", {})
        candidates.append(
            {
                "type": "Feature",
                "geometry": mapping(center),
                "properties": {
                    "parcel_id": properties.get("id"),
                    "section": properties.get("section"),
                    "number": properties.get("numero"),
                    "area_m2": round(area),
                    "zone_type": zone.get("typezone"),
                    "zone_label": zone.get("libelle"),
                    "planning_document": zone.get("idurba"),
                },
            }
        )
    if demand_payload:
        demand_features = demand_payload.get("features", [])
        demand_geometries = [shape(feature["geometry"]) for feature in demand_features]
        demand_tree = STRtree(demand_geometries)
        by_cell: dict[int, list[dict[str, object]]] = {}
        for candidate in candidates:
            center = shape(candidate["geometry"])
            matches = demand_tree.query(center, predicate="within")
            if len(matches):
                by_cell.setdefault(int(matches[0]), []).append(candidate)
        candidates = []
        for cell_index, parcels in by_cell.items():
            cell_id = demand_features[cell_index].get("properties", {}).get("id")
            parcels.sort(key=lambda item: item["properties"]["area_m2"], reverse=True)
            for parcel in parcels[:3]:
                parcel["properties"]["demand_cell_id"] = cell_id
                candidates.append(parcel)

    if not candidates:
        raise ValueError("Aucune parcelle ne respecte les contraintes préparées.")
    return {
        "type": "FeatureCollection",
        "name": "Parcelles préqualifiées — Calais",
        "metadata": {
            "territory": "62193",
            "sources": [
                "Géoportail de l'urbanisme — WFS zone_urba",
                "Cadastre Etalab",
                "OpenStreetMap — hydrographie, ODbL 1.0",
            ],
            "rules": {
                "planning_zones": ["U", "AU"],
                "minimum_area_m2": minimum_area,
                "maximum_area_m2": maximum_area,
                "water_excluded": True,
            },
        },
        "features": candidates,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("gpu_zones", type=Path)
    parser.add_argument("parcels", type=Path)
    parser.add_argument("water_mask", type=Path)
    parser.add_argument("demand_grid", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = build_candidates(
        _read(args.gpu_zones),
        _read(args.parcels),
        _read(args.water_mask),
        _read(args.demand_grid),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(f"{len(result['features'])} parcelles écrites : {args.output}")


if __name__ == "__main__":
    main()
