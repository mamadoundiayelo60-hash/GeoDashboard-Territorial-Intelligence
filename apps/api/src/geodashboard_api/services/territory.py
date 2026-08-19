"""Accès contrôlé au référentiel national des communes."""

from collections.abc import Mapping
from time import monotonic
from typing import Any, ClassVar

import httpx
from pyproj import Geod
from shapely.geometry import shape

from geodashboard_api.models import CommuneSummary, TerritoryProfile

SEARCH_FIELDS = "nom,code,codeDepartement,codeRegion,codesPostaux,population"
GEOD = Geod(ellps="WGS84")


class TerritoryServiceError(RuntimeError):
    """Erreur fonctionnelle sans détail réseau sensible."""


class TerritoryNotFoundError(TerritoryServiceError):
    """Commune absente du référentiel."""


class TerritoryService:
    """Client à hôte fixe, réponses bornées et contrats normalisés."""

    _search_cache: ClassVar[dict[str, tuple[float, list[CommuneSummary]]]] = {}
    _profile_cache: ClassVar[dict[str, tuple[float, TerritoryProfile]]] = {}
    _cache_ttl_seconds = 3_600.0

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def search(self, query: str, *, limit: int = 8) -> list[CommuneSummary]:
        """Recherche des communes par nom, code postal ou code INSEE."""
        cache_key = f"{query.casefold()}:{limit}"
        cached = self._search_cache.get(cache_key)
        if cached and monotonic() - cached[0] < self._cache_ttl_seconds:
            return cached[1]
        params: dict[str, str | int] = {
            "fields": SEARCH_FIELDS,
            "boost": "population",
            "limit": limit,
        }
        if query.isdigit() and len(query) == 5:
            params["codePostal"] = query
        elif len(query) == 5 and query.upper().isalnum() and any(c.isdigit() for c in query):
            try:
                profile = await self.get_profile(query.upper())
                result = [CommuneSummary.model_validate(profile.model_dump())]
                self._search_cache[cache_key] = (monotonic(), result)
                return result
            except TerritoryNotFoundError:
                return []
        else:
            params["nom"] = query

        payload = await self._get_json("/communes", params=params)
        if not isinstance(payload, list):
            raise TerritoryServiceError("Réponse inattendue du référentiel communal.")
        result = [self._summary(item) for item in payload[:limit] if isinstance(item, Mapping)]
        self._search_cache[cache_key] = (monotonic(), result)
        return result

    async def get_profile(self, code: str) -> TerritoryProfile:
        """Charge le contour communal et calcule ses métriques géodésiques."""
        cached = self._profile_cache.get(code)
        if cached and monotonic() - cached[0] < self._cache_ttl_seconds:
            return cached[1]
        payload = await self._get_json(
            f"/communes/{code}",
            params={"fields": SEARCH_FIELDS, "format": "geojson", "geometry": "contour"},
        )
        feature = self._as_feature(payload)
        properties = feature.get("properties")
        geometry = feature.get("geometry")
        if not isinstance(properties, Mapping) or not isinstance(geometry, Mapping):
            raise TerritoryServiceError("Le contour communal reçu est incomplet.")
        geom = shape(dict(geometry))
        if geom.is_empty or geom.geom_type not in {"Polygon", "MultiPolygon"}:
            raise TerritoryServiceError(
                "Le référentiel n'a pas fourni un polygone communal valide."
            )
        area_m2 = abs(GEOD.geometry_area_perimeter(geom)[0])
        summary = self._summary(properties)
        area_km2 = area_m2 / 1_000_000
        density = summary.population / area_km2 if summary.population is not None else None
        profile = TerritoryProfile(
            **summary.model_dump(),
            geometry=dict(geometry),
            bbox=(
                float(geom.bounds[0]),
                float(geom.bounds[1]),
                float(geom.bounds[2]),
                float(geom.bounds[3]),
            ),
            area_km2=round(area_km2, 2),
            density_per_km2=round(density, 1) if density is not None else None,
        )
        self._profile_cache[code] = (monotonic(), profile)
        return profile

    async def _get_json(self, path: str, *, params: dict[str, str | int]) -> Any:
        try:
            response = await self.client.get(path, params=params)
            if response.status_code == 404:
                raise TerritoryNotFoundError("Commune introuvable.")
            response.raise_for_status()
            if int(response.headers.get("content-length", "0")) > 5_000_000:
                raise TerritoryServiceError("La réponse du référentiel est trop volumineuse.")
            return response.json()
        except TerritoryServiceError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise TerritoryServiceError(
                "Le référentiel communal est temporairement indisponible."
            ) from exc

    @staticmethod
    def _summary(item: Mapping[str, Any]) -> CommuneSummary:
        return CommuneSummary(
            code=str(item.get("code", "")),
            name=str(item.get("nom", "Commune sans nom")),
            department_code=_optional_text(item.get("codeDepartement")),
            region_code=_optional_text(item.get("codeRegion")),
            postal_codes=[str(code) for code in item.get("codesPostaux", [])],
            population=_optional_int(item.get("population")),
        )

    @staticmethod
    def _as_feature(payload: Any) -> Mapping[str, Any]:
        if isinstance(payload, Mapping) and payload.get("type") == "Feature":
            return payload
        if isinstance(payload, Mapping) and payload.get("type") == "FeatureCollection":
            features = payload.get("features")
            if isinstance(features, list) and features and isinstance(features[0], Mapping):
                return features[0]
        raise TerritoryNotFoundError("Commune introuvable.")


def _optional_text(value: Any) -> str | None:
    return str(value) if value is not None else None


def _optional_int(value: Any) -> int | None:
    return int(value) if value is not None else None
