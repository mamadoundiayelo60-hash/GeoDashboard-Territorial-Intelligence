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
