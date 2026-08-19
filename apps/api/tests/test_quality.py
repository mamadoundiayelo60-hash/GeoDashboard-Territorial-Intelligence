"""Tests du diagnostic de qualité."""

import geopandas as gpd
from shapely.geometry import Point

from geodashboard_api.io.quality import assess_quality


def test_quality_reports_duplicates_and_nulls() -> None:
    frame = gpd.GeoDataFrame(
        {"name": ["A", None, "C"]},
        geometry=[Point(1, 2), Point(1, 2), None],
        crs="EPSG:4326",
    )
    report = assess_quality(frame)
    assert report.duplicate_geometries == 1
    assert report.empty_geometries == 1
    assert report.null_cells == 1
    assert report.score < 100
