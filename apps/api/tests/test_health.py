"""Tests du contrat minimal de l'API."""

from fastapi.testclient import TestClient

from geodashboard_api.main import app


def test_health_contract_and_security_headers() -> None:
    """Le contrôle de santé reste stable et protégé."""
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "geodashboard-api",
        "version": "0.1.0",
    }
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
