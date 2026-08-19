"""Tests du diagnostic de couverture explicable."""

import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon

from geodashboard_api.models import ScenarioLocation
from geodashboard_api.services.coverage import CoverageError, analyze_coverage


def test_scenario_increases_coverage() -> None:
    territory = Polygon([(1.83, 50.93), (1.88, 50.93), (1.88, 50.97), (1.83, 50.97)])
    equipment = gpd.GeoDataFrame({"name": ["A"]}, geometry=[Point(1.84, 50.95)], crs=4326)
    result = analyze_coverage(
        territory.__geo_interface__,
        equipment,
        500,
        70_000,
        [ScenarioLocation(longitude=1.87, latitude=50.95)],
    )
    assert result.scenario.equipment_count == 2
    assert result.scenario.coverage_rate > result.current.coverage_rate
    assert result.gain_points > 0
    assert result.current.estimated_covered_population is not None
    assert "géométrique" in result.warnings[0]


def test_coverage_rejects_non_point_layer() -> None:
    territory = Polygon([(1.83, 50.93), (1.88, 50.93), (1.88, 50.97), (1.83, 50.97)])
    polygons = gpd.GeoDataFrame(geometry=[territory], crs=4326)
    with pytest.raises(CoverageError, match="ponctuelle"):
        analyze_coverage(territory.__geo_interface__, polygons, 500, None, [])
