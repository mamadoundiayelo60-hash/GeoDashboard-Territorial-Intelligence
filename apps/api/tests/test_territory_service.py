"""Tests du référentiel communal avec transport HTTP contrôlé."""

import httpx
import pytest

from geodashboard_api.services.territory import TerritoryService


@pytest.mark.anyio
async def test_search_normalizes_communes() -> None:
    """Les détails utiles à la désambiguïsation sont conservés."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["nom"] == "Calais"
        return httpx.Response(
            200,
            json=[
                {
                    "nom": "Calais",
                    "code": "62193",
                    "codeDepartement": "62",
                    "codeRegion": "32",
                    "codesPostaux": ["62100"],
                    "population": 67544,
                }
            ],
        )

    async with httpx.AsyncClient(
        base_url="https://geo.api.gouv.fr", transport=httpx.MockTransport(handler)
    ) as client:
        results = await TerritoryService(client).search("Calais")

    assert results[0].code == "62193"
    assert results[0].department_code == "62"
    assert results[0].population == 67544


@pytest.mark.anyio
async def test_profile_computes_geodesic_metrics() -> None:
    """Une géométrie WGS84 produit une superficie et une densité positives."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/communes/62193"
        return httpx.Response(
            200,
            json={
                "type": "Feature",
                "properties": {
                    "nom": "Calais",
                    "code": "62193",
                    "codeDepartement": "62",
                    "codeRegion": "32",
                    "codesPostaux": ["62100"],
                    "population": 67544,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[1.8, 50.9], [1.9, 50.9], [1.9, 51.0], [1.8, 51.0], [1.8, 50.9]]
                    ],
                },
            },
        )

    TerritoryService._profile_cache.clear()
    async with httpx.AsyncClient(
        base_url="https://geo.api.gouv.fr", transport=httpx.MockTransport(handler)
    ) as client:
        profile = await TerritoryService(client).get_profile("62193")

    assert profile.name == "Calais"
    assert profile.area_km2 > 70
    assert profile.density_per_km2 is not None
    assert profile.bbox == (1.8, 50.9, 1.9, 51.0)
