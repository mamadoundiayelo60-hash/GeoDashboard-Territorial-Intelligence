"""Tests des validations HTTP avant tout appel externe."""

from fastapi.testclient import TestClient

from geodashboard_api.main import app


def test_invalid_insee_code_is_rejected() -> None:
    response = TestClient(app).get("/api/v1/territories/not-valid")
    assert response.status_code == 422


def test_hostile_search_characters_are_rejected() -> None:
    response = TestClient(app).get("/api/v1/territories/search", params={"q": "x<script>"})
    assert response.status_code == 422
