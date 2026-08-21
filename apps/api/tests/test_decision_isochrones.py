"""Tests du branchement des isochrones réels au diagnostic."""

from pathlib import Path

import pytest
from shapely.geometry import Polygon, mapping, shape

from geodashboard_api.models import DecisionRequest
from geodashboard_api.services.decision_isochrones import enrich_decision_with_ign
from geodashboard_api.services.ign_isochrone import IgnIsochrone, IgnIsochroneError
from geodashboard_api.services.site_selection import analyze_sites


class FakeProvider:
    async def calculate(
        self, longitude: float, latitude: float, profile: str, minutes: int
    ) -> IgnIsochrone:
        return IgnIsochrone(
            geometry=shape(
                mapping(
                    Polygon(
                        [
                            (longitude - 0.025, latitude - 0.015),
                            (longitude + 0.025, latitude - 0.015),
                            (longitude + 0.025, latitude + 0.015),
                            (longitude - 0.025, latitude + 0.015),
                        ]
                    )
                )
            ),
            resource_version="2026-08",
            profile=profile,
            minutes=minutes,
        )


class FailingProvider:
    async def calculate(
        self, longitude: float, latitude: float, profile: str, minutes: int
    ) -> IgnIsochrone:
        raise IgnIsochroneError("indisponible")


def _fixture() -> tuple[DecisionRequest, object]:
    territory = Polygon([(1.72, 50.88), (2.02, 50.88), (2.02, 51.02), (1.72, 51.02)])
    request = DecisionRequest(
        territory_geometry=mapping(territory),
        territory_name="Calais",
        territory_code="62193",
        population=67_544,
        mode="pedestrian",
        threshold_minutes=15,
    )
    demo = Path(__file__).parents[3] / "data/demo/calais-facilities-osm.geojson"
    return request, analyze_sites(request, demo)


@pytest.mark.anyio
async def test_enrichment_replaces_estimation_with_ign_geometry() -> None:
    request, initial = _fixture()
    result = await enrich_decision_with_ign(request, initial, FakeProvider(), batch_delay_seconds=0)

    assert "isochrones IGN" in result.method
    assert "réels" in result.data_status
    assert result.scenario_access_rate >= result.current_access_rate
    assert result.recommendation["gained_people"] == result.gained_people


@pytest.mark.anyio
async def test_enrichment_keeps_explicit_fallback_on_provider_failure() -> None:
    request, initial = _fixture()
    result = await enrich_decision_with_ign(
        request, initial, FailingProvider(), batch_delay_seconds=0
    )

    assert result.current_service_area == initial.current_service_area
    assert "Mode dégradé actif" in result.data_status
    assert any("repli estimé" in item for item in result.limitations)


@pytest.mark.anyio
async def test_bicycle_is_kept_as_declared_estimation() -> None:
    request, initial = _fixture()
    request.mode = "bicycle"
    result = await enrich_decision_with_ign(request, initial, FakeProvider(), batch_delay_seconds=0)

    assert "Préqualification vélo" in result.method
    assert any("profil vélo" in item for item in result.limitations)

