from pathlib import Path

from shapely.geometry import Polygon, mapping

from geodashboard_api.models import DecisionRequest
from geodashboard_api.services.site_selection import analyze_sites


def test_site_selection_returns_ranked_explainable_candidates() -> None:
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

    result = analyze_sites(request, demo)

    assert 0 <= result.current_access_rate <= result.scenario_access_rate <= 100
    assert result.gained_people > 0
    assert len(result.candidates["features"]) == 5
    assert result.recommendation["rank"] == 1
    assert result.sources
    assert result.limitations


def test_site_selection_handles_fully_served_fast_mode() -> None:
    territory = Polygon([(1.82, 50.92), (1.90, 50.92), (1.90, 50.98), (1.82, 50.98)])
    request = DecisionRequest(
        territory_geometry=mapping(territory),
        territory_name="Calais",
        territory_code="62193",
        population=67_544,
        mode="car",
        threshold_minutes=30,
    )
    demo = Path(__file__).parents[3] / "data/demo/calais-facilities-osm.geojson"

    result = analyze_sites(request, demo)

    assert result.scenario_access_rate >= result.current_access_rate
    assert len(result.candidates["features"]) >= 1


def test_site_selection_uses_real_filosofi_grid_when_available() -> None:
    territory = Polygon([(1.72, 50.88), (2.02, 50.88), (2.02, 51.02), (1.72, 51.02)])
    request = DecisionRequest(
        territory_geometry=mapping(territory),
        territory_name="Calais",
        territory_code="62193",
        population=67_544,
        mode="pedestrian",
        threshold_minutes=15,
    )
    root = Path(__file__).parents[3]
    result = analyze_sites(
        request,
        root / "data/demo/calais-facilities-osm.geojson",
        root / "data/demo/calais-filosofi-200m.geojson",
    )

    assert len(result.demand_grid["features"]) == 419
    assert "Filosofi 2021" in result.data_status
    assert any(feature["properties"]["imputed"] for feature in result.demand_grid["features"])

