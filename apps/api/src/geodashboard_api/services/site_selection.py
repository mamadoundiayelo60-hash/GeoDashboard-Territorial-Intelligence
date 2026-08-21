"""Préqualification explicable de sites d'implantation pour la démonstration V2."""

import json
from math import exp
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

from geodashboard_api.models import DecisionRequest, DecisionResult

HEALTH_AMENITIES = {"pharmacy", "clinic", "doctors", "hospital", "dentist"}
SPEED_KMH = {"pedestrian": 4.5, "bicycle": 15.0, "car": 35.0}


def _fc(features: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": features}


def _web(geometry: Any, crs: Any) -> dict[str, Any]:
    projected = gpd.GeoSeries([geometry], crs=crs).to_crs(4326).iloc[0]
    return mapping(projected)


def analyze_sites(
    request: DecisionRequest,
    demo_path: Path,
    filosofi_path: Path | None = None,
    water_mask_path: Path | None = None,
    eligible_parcels_path: Path | None = None,
) -> DecisionResult:
    """Classe des sites candidats à partir d'une maille de demande reproductible."""
    if request.territory_code != "62193":
        raise ValueError(
            "Le diagnostic décisionnel est actuellement disponible pour le territoire "
            "pilote de Calais (62193). Les autres communes peuvent être explorées, mais "
            "leur socle OSM/Filosofi doit être préparé avant tout classement."
        )
    territory_wgs = shape(request.territory_geometry)
    territory_series = gpd.GeoSeries([territory_wgs], crs=4326)
    metric_crs = territory_series.estimate_utm_crs()
    if metric_crs is None:
        raise ValueError("Projection métrique indisponible pour ce territoire.")
    territory = territory_series.to_crs(metric_crs).iloc[0]

    water_exclusion = None
    uses_water_mask = bool(water_mask_path and water_mask_path.exists())
    if uses_water_mask and water_mask_path:
        water = gpd.read_file(water_mask_path, engine="pyogrio").to_crs(metric_crs)
        if not water.empty:
            # Une marge conservative évite de proposer un site sur une berge.
            water_exclusion = unary_union(water.geometry.tolist()).buffer(20)

    all_facilities = gpd.read_file(demo_path, engine="pyogrio").to_crs(4326)
    health = all_facilities[all_facilities.get("amenity").isin(HEALTH_AMENITIES)].copy()
    health = health[health.geometry.within(territory_wgs)].to_crs(metric_crs)
    if health.empty:
        health = all_facilities.head(8).to_crs(metric_crs)

    cells: list[dict[str, Any]] = []
    uses_filosofi = bool(
        request.territory_code == "62193" and filosofi_path and filosofi_path.exists()
    )
    if uses_filosofi and filosofi_path:
        filosofi = gpd.read_file(filosofi_path, engine="pyogrio").to_crs(metric_crs)
        for feature in filosofi.itertuples():
            cell = feature.geometry.intersection(territory)
            if not cell.is_empty:
                cells.append(
                    {
                        "geometry": cell,
                        "center": cell.representative_point(),
                        "id": str(feature.id),
                        "population": max(0, round(float(feature.population))),
                        "vulnerability": float(feature.vulnerability),
                        "imputed": bool(feature.imputed),
                    }
                )
    else:
        proxies = all_facilities.to_crs(metric_crs).geometry.tolist()
        minx, miny, maxx, maxy = territory.bounds
        raw_weights: list[float] = []
        spacing = 450.0
        y = miny
        while y < maxy:
            x = minx
            while x < maxx:
                cell = box(x, y, x + spacing, y + spacing).intersection(territory)
                if not cell.is_empty and cell.area > spacing * spacing * 0.15:
                    center = cell.representative_point()
                    density = 0.15 + sum(exp(-center.distance(point) / 850.0) for point in proxies)
                    raw_weights.append(density * cell.area)
                    cells.append({"geometry": cell, "center": center})
                x += spacing
            y += spacing
        total_weight = sum(raw_weights) or 1
        populations: list[int] = []
        for item, weight in zip(cells, raw_weights, strict=True):
            population = max(1, round(request.population * weight / total_weight))
            populations.append(population)
            center = item["center"]
            item["population"] = population
            item["vulnerability"] = round(
                35 + 55 * (1 - min(1, center.distance(territory.centroid) / 5000)), 1
            )
            item["imputed"] = False
            item["id"] = f"modeled-{len(populations)}"
        delta = request.population - sum(populations)
        if cells:
            cells[0]["population"] += delta

    analysis_population = sum(item["population"] for item in cells) or request.population
    radius = SPEED_KMH[request.mode] * 1000 * request.threshold_minutes / 60 / 1.28
    facility_points = health.geometry.tolist()
    current_area = territory.intersection(
        unary_union([point.buffer(radius) for point in facility_points])
    )

    for item in cells:
        item["served"] = current_area.covers(item["center"])
    current_people = sum(item["population"] for item in cells if item["served"])

    eligible_cells = [
        item
        for item in cells
        if water_exclusion is None or not water_exclusion.covers(item["center"])
    ]
    uses_parcels = bool(eligible_parcels_path and eligible_parcels_path.exists())
    eligible_sites = eligible_cells
    if uses_parcels and eligible_parcels_path:
        parcels = gpd.read_file(eligible_parcels_path, engine="pyogrio").to_crs(metric_crs)
        cell_by_id = {item["id"]: item for item in cells}
        largest_by_cell: dict[str, Any] = {}
        for parcel in parcels.itertuples():
            cell_id = str(parcel.demand_cell_id)
            if cell_id not in largest_by_cell or parcel.area_m2 > largest_by_cell[cell_id].area_m2:
                largest_by_cell[cell_id] = parcel
        eligible_sites = []
        for cell_id, parcel in largest_by_cell.items():
            cell = cell_by_id.get(cell_id)
            if cell is None or (
                water_exclusion is not None and water_exclusion.covers(parcel.geometry)
            ):
                continue
            eligible_sites.append(
                {
                    **cell,
                    "center": parcel.geometry,
                    "parcel_id": parcel.parcel_id,
                    "parcel_area_m2": round(float(parcel.area_m2)),
                    "zone_type": parcel.zone_type,
                    "zone_label": parcel.zone_label,
                }
            )
    eligible = sorted(
        (item for item in eligible_sites if not item["served"]),
        key=lambda item: item["population"] * (1 + item["vulnerability"] / 100),
        reverse=True,
    )[:18]
    if not eligible:
        eligible = sorted(
            eligible_sites,
            key=lambda item: item["population"] * (1 + item["vulnerability"] / 100),
            reverse=True,
        )[:5]
    if not eligible:
        raise ValueError("Aucune zone candidate ne respecte les contraintes d'implantation.")
    scored: list[dict[str, Any]] = []
    max_gain = 1
    for item in eligible:
        new_area = item["center"].buffer(radius)
        beneficiaries = [
            cell for cell in cells if not cell["served"] and new_area.covers(cell["center"])
        ]
        gained = sum(cell["population"] for cell in beneficiaries)
        vulnerable = sum(cell["population"] * cell["vulnerability"] / 100 for cell in beneficiaries)
        max_gain = max(max_gain, gained)
        scored.append({"item": item, "gained": gained, "vulnerable": vulnerable})
    max_vulnerable = max((row["vulnerable"] for row in scored), default=1) or 1
    for row in scored:
        isolation = min(
            (row["item"]["center"].distance(point) for point in facility_points), default=radius * 2
        )
        equity = min(1.0, isolation / (radius * 1.5))
        row["score"] = 100 * (
            request.weights.population * row["gained"] / max_gain
            + request.weights.vulnerability * row["vulnerable"] / max_vulnerable
            + request.weights.equity * equity
        )
    scored.sort(key=lambda row: row["score"], reverse=True)
    top = scored[0]
    scenario_area = territory.intersection(current_area.union(top["item"]["center"].buffer(radius)))
    scenario_people = current_people + top["gained"]

    grid_features = []
    for item in cells:
        grid_features.append(
            {
                "type": "Feature",
                "geometry": _web(item["geometry"], metric_crs),
                "properties": {
                    "population": item["population"],
                    "vulnerability": item["vulnerability"],
                    "served": item["served"],
                    "imputed": item["imputed"],
                },
            }
        )
    candidate_features = []
    for rank, row in enumerate(scored[:5], 1):
        candidate_features.append(
            {
                "type": "Feature",
                "geometry": _web(row["item"]["center"], metric_crs),
                "properties": {
                    "rank": rank,
                    "score": round(row["score"], 1),
                    "gained_people": row["gained"],
                    "vulnerable_people": round(row["vulnerable"]),
                    "constraint_status": "Hors masque hydrographique",
                    "parcel_id": row["item"].get("parcel_id"),
                    "parcel_area_m2": row["item"].get("parcel_area_m2"),
                    "zone_type": row["item"].get("zone_type"),
                    "zone_label": row["item"].get("zone_label"),
                },
            }
        )

    health_wgs = health.to_crs(4326)
    facility_features = json.loads(health_wgs.to_json(drop_id=True))
    gain_rate = top["gained"] / analysis_population * 100
    recommendation = {
        "rank": 1,
        "score": round(top["score"], 1),
        "gained_people": top["gained"],
        "longitude": round(_web(top["item"]["center"], metric_crs)["coordinates"][0], 6),
        "latitude": round(_web(top["item"]["center"], metric_crs)["coordinates"][1], 6),
        "parcel_id": top["item"].get("parcel_id"),
        "parcel_area_m2": top["item"].get("parcel_area_m2"),
        "planning_zone": top["item"].get("zone_label"),
        "explanation": (
            "Le site A maximise le gain de population et dessert en priorité "
            f"des mailles vulnérables : +{top['gained']:,} habitants accessibles."
        ).replace(",", " "),
    }
    return DecisionResult(
        method="Préqualification multimodale — distance réseau estimée, calibration IGN à venir",
        data_status=(
            "Équipements OSM, INSEE Filosofi 2021, hydrographie OSM, zonage GPU "
            "et parcelles cadastrales réels."
            if uses_filosofi and uses_water_mask and uses_parcels
            else "Équipements OSM, carreaux INSEE Filosofi 2021 et masque hydrographique OSM réels."
            if uses_filosofi and uses_water_mask
            else "Équipements OSM réels et carreaux INSEE Filosofi 2021 réels."
            if uses_filosofi
            else "Population communale officielle et répartition infracommunale modélisée."
        ),
        current_access_rate=round(current_people / analysis_population * 100, 1),
        scenario_access_rate=round(scenario_people / analysis_population * 100, 1),
        gained_people=top["gained"],
        underserved_people=max(0, analysis_population - current_people),
        equity_gain=round(gain_rate, 1),
        facilities=facility_features,
        demand_grid=_fc(grid_features),
        candidates=_fc(candidate_features),
        current_service_area=_web(current_area, metric_crs),
        scenario_service_area=_web(scenario_area, metric_crs),
        recommendation=recommendation,
        sources=[
            {"name": "Population communale", "provider": "API Découpage administratif / INSEE"},
            *(
                [
                    {
                        "name": "Population et vulnérabilité",
                        "provider": "INSEE — Filosofi 2021, carreaux de 200 m",
                    }
                ]
                if uses_filosofi
                else []
            ),
            *(
                [
                    {
                        "name": "Zonage réglementaire",
                        "provider": "Géoportail de l'urbanisme — PLUi en production",
                    },
                    {"name": "Parcelles", "provider": "Cadastre Etalab"},
                ]
                if uses_parcels
                else []
            ),
            {"name": "Équipements de santé", "provider": "OpenStreetMap — ODbL 1.0"},
            *(
                [
                    {
                        "name": "Exclusions hydrographiques",
                        "provider": "OpenStreetMap — ODbL 1.0",
                    }
                ]
                if uses_water_mask
                else []
            ),
            {"name": "Réseau cible", "provider": "Géoplateforme IGN — BD TOPO®"},
        ],
        limitations=[
            *(
                ["94 carreaux Filosofi de Calais sont imputés conformément au secret statistique."]
                if uses_filosofi
                else ["La maille de population est modélisée dans ce démonstrateur."]
            ),
            "Les temps affichés sont une préqualification ; la V2 finale appellera "
            "les isochrones IGN.",
            "Le classement aide à comparer des zones et ne remplace pas une étude "
            "foncière ou une instruction d'urbanisme. Les parcelles sont situées en "
            "zone U/AU et hors eau, mais le règlement écrit, la propriété, les réseaux "
            "et les servitudes doivent encore être vérifiés.",
        ],
    )
