"""Test d'intégration du diagnostic guidé."""

import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from geodashboard_api.config import Settings, get_settings
from geodashboard_api.main import app


def test_coverage_endpoint_compares_scenario(tmp_path: Path) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(runtime_data_dir=tmp_path)
    client = TestClient(app)
    session = str(uuid4())
    layer_payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "A"},
                "geometry": {"type": "Point", "coordinates": [1.84, 50.95]},
            }
        ],
    }
    imported = client.post(
        "/api/v1/layers/upload",
        headers={"X-Session-ID": session},
        files={"file": ("services.geojson", json.dumps(layer_payload), "application/geo+json")},
    ).json()
    response = client.post(
        "/api/v1/diagnostics/coverage",
        headers={"X-Session-ID": session},
        json={
            "layer_id": imported["id"],
            "territory_geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[1.83, 50.93], [1.88, 50.93], [1.88, 50.97], [1.83, 50.97], [1.83, 50.93]]
                ],
            },
            "distance_m": 500,
            "population": 70_000,
            "scenario_locations": [{"longitude": 1.87, "latitude": 50.95}],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["gain_points"] > 0
    app.dependency_overrides.clear()
