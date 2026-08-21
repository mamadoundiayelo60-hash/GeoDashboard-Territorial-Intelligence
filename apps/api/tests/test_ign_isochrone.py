"""Tests du connecteur officiel d'isochrones IGN."""

import httpx
import pytest

from geodashboard_api.services.ign_isochrone import IgnIsochroneClient, IgnIsochroneError


@pytest.mark.anyio
async def test_calculate_parses_geojson_and_uses_cache() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.url.path == "/navigation/isochrone"
        return httpx.Response(
            200,
            json={
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "properties": {"resourceVersion": "2026-08"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[1.8, 50.9], [1.9, 50.9], [1.9, 51.0], [1.8, 50.9]]],
                    },
                }],
            },
        )

    IgnIsochroneClient._cache.clear()
    async with httpx.AsyncClient(
        base_url="https://data.geopf.fr/navigation",
        transport=httpx.MockTransport(handler),
    ) as client:
        service = IgnIsochroneClient(client)
        first = await service.calculate(1.86, 50.95, "pedestrian", 15)
        second = await service.calculate(1.86, 50.95, "pedestrian", 15)

    assert first.geometry.geom_type == "Polygon"
    assert first.resource_version == "2026-08"
    assert second is first
    assert calls == 1


@pytest.mark.anyio
async def test_calculate_rejects_unsupported_bicycle_profile() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Aucun appel réseau ne doit être effectué.")

    async with httpx.AsyncClient(
        base_url="https://data.geopf.fr/navigation",
        transport=httpx.MockTransport(handler),
    ) as client:
        service = IgnIsochroneClient(client)
        with pytest.raises(ValueError, match="profil IGN"):
            await service.calculate(1.86, 50.95, "bicycle", 15)


@pytest.mark.anyio
async def test_calculate_masks_provider_failures() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "provider failure"})

    IgnIsochroneClient._cache.clear()
    async with httpx.AsyncClient(
        base_url="https://data.geopf.fr/navigation",
        transport=httpx.MockTransport(handler),
    ) as client:
        service = IgnIsochroneClient(client)
        with pytest.raises(IgnIsochroneError, match="temporairement indisponible"):
            await service.calculate(1.86, 50.95, "car", 10)

