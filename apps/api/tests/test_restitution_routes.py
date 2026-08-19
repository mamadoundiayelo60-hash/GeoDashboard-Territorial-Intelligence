"""Test d'intégration du téléchargement PDF."""

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from geodashboard_api.config import Settings, get_settings
from geodashboard_api.main import app
from tests.test_reporting import report_payload


def test_report_endpoint_returns_pdf(tmp_path: Path) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(runtime_data_dir=tmp_path)
    response = TestClient(app).post(
        "/api/v1/restitution/reports",
        headers={"X-Session-ID": str(uuid4())},
        json=report_payload(),
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    app.dependency_overrides.clear()
