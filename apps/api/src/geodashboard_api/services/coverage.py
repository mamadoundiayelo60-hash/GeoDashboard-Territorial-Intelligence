"""Diagnostic explicable de couverture par distance euclidienne."""

import json
from typing import Any, cast

import geopandas as gpd
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from geodashboard_api.models import CoverageIndicators, CoverageResult, ScenarioLocation


class CoverageError(ValueError):
    """Erreur métier présentable à l'utilisateur."""


def analyze_coverage(
    territory_geometry: dict[str, Any],
    equipment_frame: gpd.GeoDataFrame,
    distance_m: float,
    population: int | None,
    scenario_locations: list[ScenarioLocation],
) -> CoverageResult:
    """Compare la situation actuelle à un scénario d'implantation."""
    territory = shape(territory_geometry)
    if (
        territory.is_empty
        or not territory.is_valid
        or territory.geom_type not in {"Polygon", "MultiPolygon"}
    ):
        raise CoverageError("La géométrie du territoire est invalide.")
    points = equipment_frame.to_crs(4326)
    points = points[points.geometry.geom_type.isin(["Point", "MultiPoint"])]
    if points.empty:
        raise CoverageError("Le diagnostic de couverture nécessite une couche ponctuelle.")
    territory_frame = gpd.GeoSeries([territory], crs=4326)
    projected_crs = territory_frame.estimate_utm_crs()
    if projected_crs is None:
        raise CoverageError("Aucun système métrique adapté n'a pu être déterminé.")
    territory_metric = territory_frame.to_crs(projected_crs).iloc[0]
    points_metric = points.to_crs(projected_crs)
    source_points = [
        geometry
        for geometry in points_metric.geometry
        if geometry is not None and not geometry.is_empty
    ]
    current_covered = _coverage_geometry(territory_metric, source_points, distance_m)
    scenario_wgs84 = gpd.GeoSeries(
        [Point(location.longitude, location.latitude) for location in scenario_locations], crs=4326
    )
    scenario_points = list(source_points)
    if len(scenario_wgs84):
        scenario_points.extend(scenario_wgs84.to_crs(projected_crs).tolist())
    scenario_covered = _coverage_geometry(territory_metric, scenario_points, distance_m)
    current = _indicators(territory_metric, current_covered, len(source_points), population)
    scenario = _indicators(territory_metric, scenario_covered, len(scenario_points), population)
    gain = round(scenario.coverage_rate - current.coverage_rate, 2)
    if gain >= 10:
        interpretation = f"Le scénario améliore nettement la couverture de {gain:.1f} points."
    elif gain > 0:
        interpretation = f"Le scénario apporte un gain ciblé de {gain:.1f} points."
    else:
        interpretation = "Le scénario ne produit pas de gain mesurable sur ce territoire."
    return CoverageResult(
        method="Buffer euclidien intersecté au territoire",
        distance_m=distance_m,
        current=current,
        scenario=scenario,
        gain_points=gain,
        covered_geometry=_web_geometry(current_covered, projected_crs),
        uncovered_geometry=_web_geometry(
            territory_metric.difference(current_covered), projected_crs
        ),
        scenario_covered_geometry=_web_geometry(scenario_covered, projected_crs),
        scenario_uncovered_geometry=_web_geometry(
            territory_metric.difference(scenario_covered), projected_crs
        ),
        interpretation=interpretation,
        warnings=[
            "Cette couverture est géométrique : elle ne représente ni un temps de trajet "
            "ni une distance réseau.",
            "La population couverte est une estimation proportionnelle à la surface, "
            "faute de grille de population.",
        ],
    )


def _coverage_geometry(
    territory: BaseGeometry, points: list[BaseGeometry], distance_m: float
) -> BaseGeometry:
    return territory.intersection(unary_union([point.buffer(distance_m) for point in points]))


def _indicators(
    territory: BaseGeometry,
    covered: BaseGeometry,
    equipment_count: int,
    population: int | None,
) -> CoverageIndicators:
    total_area = territory.area
    covered_area = covered.area
    rate = min(100.0, (covered_area / total_area * 100) if total_area else 0.0)
    return CoverageIndicators(
        equipment_count=equipment_count,
        covered_area_km2=round(covered_area / 1_000_000, 3),
        uncovered_area_km2=round(max(0, total_area - covered_area) / 1_000_000, 3),
        coverage_rate=round(rate, 2),
        estimated_covered_population=round(population * rate / 100)
        if population is not None
        else None,
    )


def _web_geometry(geometry: BaseGeometry, crs: Any) -> dict[str, Any]:
    series = gpd.GeoSeries([geometry], crs=crs).to_crs(4326)
    return cast(dict[str, Any], json.loads(series.to_json())["features"][0]["geometry"])
