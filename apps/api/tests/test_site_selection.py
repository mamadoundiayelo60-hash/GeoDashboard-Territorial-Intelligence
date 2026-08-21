from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Polygon, mapping, shape
from shapely.ops import unary_union

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


def test_site_selection_rejects_unprepared_territory() -> None:
    territory = Polygon([(2.22, 48.81), (2.42, 48.81), (2.42, 48.91), (2.22, 48.91)])
    request = DecisionRequest(
        territory_geometry=mapping(territory),
        territory_name="Paris",
        territory_code="75056",
        population=2_100_000,
    )
    demo = Path(__file__).parents[3] / "data/demo/calais-facilities-osm.geojson"

    with pytest.raises(ValueError, match="territoire pilote de Calais"):
        analyze_sites(request, demo)


def test_candidates_are_outside_hydrographic_exclusion() -> None:
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
    water_path = root / "data/demo/calais-water-mask.geojson"
    result = analyze_sites(
        request,
        root / "data/demo/calais-facilities-osm.geojson",
        root / "data/demo/calais-filosofi-200m.geojson",
        water_path,
    )

    water = gpd.read_file(water_path, engine="pyogrio").to_crs(32631)
    exclusion = unary_union(water.geometry.tolist()).buffer(20)
    candidates = gpd.GeoSeries(
        [shape(feature["geometry"]) for feature in result.candidates["features"]],
        crs=4326,
    ).to_crs(32631)

    assert all(not exclusion.covers(point) for point in candidates)
    assert all(
        feature["properties"]["constraint_status"] == "Hors masque hydrographique"
        for feature in result.candidates["features"]
    )
    assert "masque hydrographique" in result.data_status
