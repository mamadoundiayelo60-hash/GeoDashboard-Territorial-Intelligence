"""API du studio de décision territoriale V2."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException

from geodashboard_api.config import Settings, get_settings
from geodashboard_api.models import DecisionRequest, DecisionResult
from geodashboard_api.services.decision_isochrones import enrich_decision_with_ign
from geodashboard_api.services.ign_isochrone import IgnIsochroneClient
from geodashboard_api.services.site_selection import analyze_sites

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.post("/site-selection", response_model=DecisionResult)
async def site_selection(
    request: DecisionRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> DecisionResult:
    """Produit un diagnostic et cinq sites candidats explicables."""
    try:
        result = analyze_sites(
            request,
            settings.demo_data_path,
            settings.filosofi_demo_path,
            settings.water_mask_path,
            settings.eligible_parcels_path,
        )
        async with httpx.AsyncClient(
            base_url=settings.ign_navigation_base_url,
            timeout=httpx.Timeout(settings.ign_navigation_timeout_seconds),
            limits=httpx.Limits(max_connections=4, max_keepalive_connections=4),
            trust_env=False,
        ) as client:
            return await enrich_decision_with_ign(request, result, IgnIsochroneClient(client))
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
