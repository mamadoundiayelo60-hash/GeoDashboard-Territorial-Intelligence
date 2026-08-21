"""Enrichissement d'un diagnostic par des isochrones réseau IGN réels."""

import asyncio
from collections.abc import Sequence
from typing import Protocol

from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from geodashboard_api.models import DecisionRequest, DecisionResult
from geodashboard_api.services.ign_isochrone import IgnIsochrone, IgnIsochroneError


class IsochroneProvider(Protocol):
    """Contrat minimal permettant de tester le moteur sans appel réseau."""

    async def calculate(
        self, longitude: float, latitude: float, profile: str, minutes: int
    ) -> IgnIsochrone: ...


async def _calculate_in_batches(
    provider: IsochroneProvider,
    coordinates: Sequence[tuple[float, float]],
    profile: str,
    minutes: int,
    batch_delay_seconds: float,
) -> list[IgnIsochrone]:
    """Respecte la limite IGN de cinq requêtes par seconde avec une marge."""
    results: list[IgnIsochrone] = []
    batch_size = 4
    for start in range(0, len(coordinates), batch_size):
        batch = coordinates[start : start + batch_size]
        results.extend(
            await asyncio.gather(
                *(provider.calculate(lon, lat, profile, minutes) for lon, lat in batch)
            )
        )
        if start + batch_size < len(coordinates) and batch_delay_seconds:
            await asyncio.sleep(batch_delay_seconds)
    return results


async def enrich_decision_with_ign(
    request: DecisionRequest,
    result: DecisionResult,
    provider: IsochroneProvider,
    *,
    batch_delay_seconds: float = 1.05,
) -> DecisionResult:
    """Recalcule la couverture avec le réseau IGN ou conserve le repli estimé."""
    if request.mode == "bicycle":
        return result.model_copy(
            update={
                "method": (
                    "Préqualification vélo — vitesse conventionnelle, réseau IGN indisponible"
                ),
                "limitations": [
                    *result.limitations,
                    "Le profil vélo n'est pas proposé par l'API d'isochrones IGN.",
                ],
            }
        )

    facility_coordinates = [
        tuple(feature["geometry"]["coordinates"])
        for feature in result.facilities.get("features", [])
        if feature.get("geometry", {}).get("type") == "Point"
    ]
    candidates = result.candidates.get("features", [])
    if not facility_coordinates or not candidates:
        return result
    candidate_coordinates = tuple(candidates[0]["geometry"]["coordinates"])

    try:
        isochrones = await _calculate_in_batches(
            provider,
            [*facility_coordinates, candidate_coordinates],
            request.mode,
            request.threshold_minutes,
            batch_delay_seconds,
        )
    except (IgnIsochroneError, ValueError):
        return result.model_copy(
            update={
                "data_status": f"{result.data_status} Mode dégradé actif : IGN indisponible.",
                "limitations": [
                    *result.limitations,
                    "L'API IGN n'a pas répondu : les zones affichées utilisent le repli estimé.",
                ],
            }
        )

    territory = shape(request.territory_geometry)
    current_area = territory.intersection(unary_union([item.geometry for item in isochrones[:-1]]))
    scenario_area = territory.intersection(current_area.union(isochrones[-1].geometry))
    current_people = 0
    scenario_people = 0
    analysis_population = (
        sum(
            int((feature.get("properties") or {}).get("population") or 0)
            for feature in result.demand_grid.get("features", [])
        )
        or request.population
    )
    grid = result.demand_grid.copy()
    grid["features"] = []
    for feature in result.demand_grid.get("features", []):
        center = shape(feature["geometry"]).representative_point()
        properties = dict(feature.get("properties") or {})
        properties["served"] = current_area.covers(center)
        population = int(properties.get("population") or 0)
        if properties["served"]:
            current_people += population
        if scenario_area.covers(center):
            scenario_people += population
        grid["features"].append({**feature, "properties": properties})

    gained = max(0, scenario_people - current_people)
    versions = sorted({item.resource_version for item in isochrones if item.resource_version})
    actionable = gained > 0
    recommendation = dict(result.recommendation)
    recommendation["gained_people"] = gained
    recommendation["explanation"] = (
        (
            "Le site A est préqualifié par le modèle multicritère ; son impact est ensuite "
            f"mesuré sur le réseau IGN : +{gained:,} habitants accessibles."
        ).replace(",", " ")
        if actionable
        else (
            "Aucune nouvelle implantation prioritaire : l'isochrone IGN ne mesure aucun "
            "gain au seuil choisi. Le moteur ne formule donc pas de recommandation artificielle."
        )
    )
    if not actionable:
        recommendation.update({"rank": 0, "score": 0})
    candidates_updated = result.candidates.copy()
    candidates_updated["features"] = [dict(feature) for feature in candidates]
    top_properties = dict(candidates_updated["features"][0].get("properties") or {})
    top_properties["gained_people"] = gained
    candidates_updated["features"][0] = {
        **candidates_updated["features"][0],
        "properties": top_properties,
    }
    if not actionable:
        candidates_updated["features"] = []
        scenario_area = current_area
        scenario_people = current_people
    version_label = ", ".join(versions) if versions else "version fournie par le service"
    return result.model_copy(
        update={
            "method": (
                "Préqualification multicritère puis mesure par isochrones IGN "
                f"BD TOPO® ({version_label})"
            ),
            "data_status": (
                "Isochrones réseau IGN réels ; équipements OSM réels ; "
                + (
                    "population et vulnérabilité INSEE Filosofi 2021 réelles."
                    if "Filosofi" in result.data_status
                    else "répartition infracommunale modélisée."
                )
            ),
            "current_access_rate": round(current_people / analysis_population * 100, 1),
            "scenario_access_rate": round(scenario_people / analysis_population * 100, 1),
            "gained_people": gained,
            "has_actionable_gain": actionable,
            "decision_message": None if actionable else recommendation["explanation"],
            "underserved_people": max(0, analysis_population - current_people),
            "equity_gain": round(gained / analysis_population * 100, 1),
            "demand_grid": grid,
            "candidates": candidates_updated,
            "current_service_area": mapping(current_area),
            "scenario_service_area": mapping(scenario_area),
            "recommendation": recommendation,
            "limitations": [
                limitation
                for limitation in result.limitations
                if "isochrones IGN" not in limitation
            ],
        }
    )
