"""Recherche et profil des territoires communaux."""

import re
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from geodashboard_api.config import Settings, get_settings
from geodashboard_api.models import CommuneSummary, TerritoryProfile
from geodashboard_api.services.territory import (
    TerritoryNotFoundError,
    TerritoryService,
    TerritoryServiceError,
)

router = APIRouter(prefix="/territories", tags=["territories"])
SAFE_QUERY = re.compile(r"^[\wÀ-ÖØ-öø-ÿ' .-]+$", re.UNICODE)


async def territory_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> TerritoryService:
    """Construit un client borné vers l'unique hôte public autorisé."""
    client = httpx.AsyncClient(
        base_url=settings.geo_api_base_url,
        timeout=httpx.Timeout(settings.geo_api_timeout_seconds),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        follow_redirects=False,
        trust_env=False,
        headers={"User-Agent": "GeoDashboard/0.1 (+territorial-analysis)"},
    )
    return TerritoryService(client)


@router.get("/search", response_model=list[CommuneSummary])
async def search_territories(
    q: Annotated[str, Query(min_length=2, max_length=80)],
    service: Annotated[TerritoryService, Depends(territory_service)],
) -> list[CommuneSummary]:
    """Retourne au plus huit communes sans ambiguïté silencieuse."""
    query = q.strip()
    if not SAFE_QUERY.fullmatch(query):
        raise HTTPException(status_code=422, detail="La recherche contient des caractères refusés.")
    try:
        return await service.search(query)
    except TerritoryServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        await service.client.aclose()


@router.get("/{code}", response_model=TerritoryProfile)
async def get_territory(
    code: str,
    service: Annotated[TerritoryService, Depends(territory_service)],
) -> TerritoryProfile:
    """Retourne le contour officiel et les indicateurs de base."""
    normalized = code.upper()
    if not re.fullmatch(r"[0-9A-Z]{5}", normalized):
        raise HTTPException(status_code=422, detail="Code INSEE invalide.")
    try:
        return await service.get_profile(normalized)
    except TerritoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TerritoryServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        await service.client.aclose()
