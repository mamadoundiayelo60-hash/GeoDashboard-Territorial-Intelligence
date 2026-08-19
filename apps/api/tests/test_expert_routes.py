"""Test d'intégration d'un champ calculé et de son historique."""

import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from geodashboard_api.config import Settings, get_settings
from geodashboard_api.main import app


def test_calculated_field_is_persisted_and_audited(tmp_path: Path) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(runtime_data_dir=tmp_path)
    client = TestClient(app)
    session = str(uuid4())
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"capacity": 20},
                "geometry": {"type": "Point", "coordinates": [1.85, 50.95]},
            }
        ],
    }
    imported = client.post(
        "/api/v1/layers/upload",
        headers={"X-Session-ID": session},
        files={"file": ("sites.geojson", json.dumps(payload), "application/geo+json")},
    ).json()
    response = client.post(
        "/api/v1/expert/calculated-fields",
        headers={"X-Session-ID": session},
        json={"layer_id": imported["id"], "field_name": "double_cap", "expression": "capacity * 2"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["preview"] == [40]
    assert response.json()["layer"]["field_count"] == 2
    history = client.get("/api/v1/expert/history", headers={"X-Session-ID": session}).json()
    assert history[0]["event_type"] == "calculated_field"
    app.dependency_overrides.clear()
