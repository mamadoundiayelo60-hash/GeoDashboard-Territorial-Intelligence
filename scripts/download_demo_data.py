"""Télécharge un petit extrait OSM reproductible pour la démonstration Calais."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

ENDPOINT = "https://overpass-api.de/api/interpreter"
QUERY = """
[out:json][timeout:20];
area["ref:INSEE"="62193"]->.territory;
(nwr["amenity"~"school|college|hospital|clinic|pharmacy"](area.territory););
out center tags;
"""
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "demo" / "calais-facilities-osm.geojson"


def main() -> None:
    """Interroge l'hôte fixé, normalise les centroïdes et écrit le GeoJSON."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", type=Path, help="Réponse Overpass JSON déjà téléchargée"
    )
    arguments = parser.parse_args()
    if arguments.input:
        payload = json.loads(arguments.input.read_text(encoding="utf-8"))
    else:
        with httpx.Client(
            timeout=30, follow_redirects=False, trust_env=False
        ) as client:
            response = client.get(ENDPOINT, params={"data": QUERY})
            response.raise_for_status()
            payload = response.json()
    features = []
    for element in payload.get("elements", []):
        longitude = element.get("lon") or element.get("center", {}).get("lon")
        latitude = element.get("lat") or element.get("center", {}).get("lat")
        if longitude is None or latitude is None:
            continue
        tags = element.get("tags", {})
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
                "properties": {
                    "name": tags.get("name", "Équipement sans nom"),
                    "amenity": tags.get("amenity", "unknown"),
                    "osm_type": element.get("type"),
                    "osm_id": element.get("id"),
                    "source": "OpenStreetMap contributors",
                },
            }
        )
    collection = {
        "type": "FeatureCollection",
        "name": "Équipements de proximité - Calais",
        "metadata": {
            "source": "OpenStreetMap contributors",
            "license": "ODbL 1.0",
            "query": "amenity=school|college|hospital|clinic|pharmacy",
            "territory_code": "62193",
            "retrieved_at": datetime.now(UTC).isoformat(),
        },
        "features": features,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(collection, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"{len(features)} équipements écrits dans {OUTPUT}")


if __name__ == "__main__":
    main()
