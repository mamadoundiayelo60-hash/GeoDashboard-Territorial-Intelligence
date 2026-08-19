"""Test d'intégration d'un import GeoJSON isolé par session."""

import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from geodashboard_api.config import Settings, get_settings
from geodashboard_api.main import app


def test_upload_list_and_delete_layer(tmp_path: Path) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(runtime_data_dir=tmp_path)
    client = TestClient(app)
    session = str(uuid4())
    payload = {
        "type": "FeatureCollection",
        "name": "schools",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "École test"},
                "geometry": {"type": "Point", "coordinates": [1.85, 50.95]},
            }
        ],
    }
    response = client.post(
        "/api/v1/layers/upload",
        headers={"X-Session-ID": session},
        files={"file": ("schools.geojson", json.dumps(payload), "application/geo+json")},
    )
    assert response.status_code == 201, response.text
    layer = response.json()
    assert layer["feature_count"] == 1
    assert layer["quality"]["score"] == 100

    catalog = client.get("/api/v1/layers", headers={"X-Session-ID": session})
    assert [item["id"] for item in catalog.json()] == [layer["id"]]

    deleted = client.delete(f"/api/v1/layers/{layer['id']}", headers={"X-Session-ID": session})
    assert deleted.status_code == 204
    app.dependency_overrides.clear()


def test_loads_packaged_demo_once(tmp_path: Path) -> None:
    demo_path = Path(__file__).parents[3] / "data" / "demo" / "calais-facilities-osm.geojson"
    app.dependency_overrides[get_settings] = lambda: Settings(
        runtime_data_dir=tmp_path, demo_data_path=demo_path
    )
    client = TestClient(app)
    headers = {"X-Session-ID": str(uuid4())}
    first = client.post("/api/v1/layers/demo", headers=headers)
    second = client.post("/api/v1/layers/demo", headers=headers)
    assert first.status_code == 201, first.text
    assert first.json()["feature_count"] == 103
    assert second.json()["id"] == first.json()["id"]
    assert first.json()["source_format"] == "demo_osm"
    app.dependency_overrides.clear()
