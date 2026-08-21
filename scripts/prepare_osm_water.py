#!/usr/bin/env python3
"""Convertit une réponse Overpass hydrographique en masque GeoJSON polygonal."""

import argparse
import json
from pathlib import Path

from shapely.geometry import Polygon, mapping
from shapely.ops import unary_union


def _polygon(points: list[dict[str, float]]) -> Polygon | None:
    coordinates = [(point["lon"], point["lat"]) for point in points]
    if len(coordinates) < 4 or coordinates[0] != coordinates[-1]:
        return None
    polygon = Polygon(coordinates)
    return polygon if polygon.is_valid and not polygon.is_empty else None


def build_mask(payload: dict[str, object]) -> dict[str, object]:
    """Fusionne les contours fermés OSM sans dupliquer les membres de relations."""
    polygons = []
    for element in payload.get("elements", []):
        if element.get("type") == "way" and element.get("geometry"):
            polygon = _polygon(element["geometry"])
            if polygon:
                polygons.append(polygon)
        if element.get("type") == "relation":
            for member in element.get("members", []):
                if member.get("role") == "outer" and member.get("geometry"):
                    polygon = _polygon(member["geometry"])
                    if polygon:
                        polygons.append(polygon)
    if not polygons:
        raise ValueError("Aucune surface hydrographique fermée dans la réponse Overpass.")
    geometry = unary_union(polygons).buffer(0)
    return {
        "type": "FeatureCollection",
        "name": "Masque hydrographique Calais",
        "metadata": {"source": "OpenStreetMap — ODbL 1.0", "purpose": "exclusion"},
        "features": [
            {
                "type": "Feature",
                "properties": {"constraint": "water"},
                "geometry": mapping(geometry),
            }
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("overpass_json", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = build_mask(json.loads(args.overpass_json.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    print(f"Masque écrit : {args.output}")


if __name__ == "__main__":
    main()
