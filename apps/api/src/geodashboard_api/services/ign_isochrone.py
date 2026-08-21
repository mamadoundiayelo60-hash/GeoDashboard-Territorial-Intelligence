"""Client borné et résilient pour les isochrones de la Géoplateforme IGN."""

from dataclasses import dataclass
from time import monotonic
from typing import Any, ClassVar

import httpx
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry


class IgnIsochroneError(RuntimeError):
    """Erreur fonctionnelle masquant les détails réseau du fournisseur externe."""


@dataclass(frozen=True)
class IgnIsochrone:
    """Isochrone normalisée et informations de traçabilité associées."""

    geometry: BaseGeometry
    resource_version: str | None
    profile: str
    minutes: int


class IgnIsochroneClient:
    """Interroge l'IGN avec cache mémoire et paramètres strictement contrôlés."""

    _cache: ClassVar[dict[tuple[float, float, str, int], tuple[float, IgnIsochrone]]] = {}
    _cache_ttl_seconds = 86_400.0
    _profiles: ClassVar[set[str]] = {"pedestrian", "car"}

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def calculate(
        self,
        longitude: float,
        latitude: float,
        profile: str,
        minutes: int,
    ) -> IgnIsochrone:
        """Calcule un isochrone temps en EPSG:4326 ou retourne sa version en cache."""
        if profile not in self._profiles:
            raise ValueError("Le profil IGN doit être 'pedestrian' ou 'car'.")
        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
            raise ValueError("Coordonnées WGS84 invalides.")
        if not 5 <= minutes <= 30:
            raise ValueError("La durée doit être comprise entre 5 et 30 minutes.")

        key = (round(longitude, 6), round(latitude, 6), profile, minutes)
        cached = self._cache.get(key)
        if cached and monotonic() - cached[0] < self._cache_ttl_seconds:
            return cached[1]

        payload = {
            "point": f"{longitude:.6f},{latitude:.6f}",
            "resource": "bdtopo-valhalla",
            "costValue": str(minutes),
            "costType": "time",
            "profile": profile,
            "direction": "departure",
            "geometryFormat": "geojson",
            "timeUnit": "minute",
            "distanceUnit": "meter",
            "crs": "EPSG:4326",
        }
        try:
            response = await self.client.post("/isochrone", json=payload)
            response.raise_for_status()
            data = response.json()
            geometry_data = self._extract_geometry(data)
            geometry = shape(geometry_data)
            if geometry.is_empty or geometry.geom_type not in {"Polygon", "MultiPolygon"}:
                raise ValueError("Géométrie d'isochrone invalide.")
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
            raise IgnIsochroneError(
                "Le service d'isochrone IGN est temporairement indisponible."
            ) from exc

        result = IgnIsochrone(
            geometry=geometry,
            resource_version=self._extract_resource_version(data),
            profile=profile,
            minutes=minutes,
        )
        self._cache[key] = (monotonic(), result)
        return result

    @staticmethod
    def _extract_geometry(data: dict[str, Any]) -> dict[str, Any]:
        """Accepte les enveloppes GeoJSON documentées et leurs variantes fournisseur."""
        if data.get("type") == "FeatureCollection":
            features = data.get("features") or []
            return features[0]["geometry"]
        if data.get("type") == "Feature":
            return data["geometry"]
        if isinstance(data.get("geometry"), dict):
            return data["geometry"]
        raise ValueError("Réponse IGN sans géométrie exploitable.")

    @staticmethod
    def _extract_resource_version(data: dict[str, Any]) -> str | None:
        properties = data.get("properties") or {}
        if data.get("type") == "FeatureCollection" and data.get("features"):
            properties = data["features"][0].get("properties") or properties
        value = properties.get("resourceVersion") or data.get("resourceVersion")
        return str(value) if value is not None else None

