"""API du studio de décision territoriale V2."""

from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException

from geodashboard_api.config import Settings, get_settings
from geodashboard_api.io.layer_store import LayerStore
from geodashboard_api.models import DecisionRequest, DecisionResult
from geodashboard_api.services.decision_isochrones import enrich_decision_with_ign
from geodashboard_api.services.ign_isochrone import IgnIsochroneClient
from geodashboard_api.services.site_selection import analyze_sites

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.post("/site-selection", response_model=DecisionResult)
async def site_selection(
    request: DecisionRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    x_session_id: Annotated[str | None, Header()] = None,
) -> DecisionResult:
    """Produit un diagnostic et cinq sites candidats explicables."""
    try:
        custom_facilities = None
        if request.equipment_layer_id:
            if not x_session_id:
                raise ValueError("La session de la couche importée est absente.")
            try:
                store = LayerStore(settings.runtime_data_dir, UUID(x_session_id))
                custom_facilities = store.load_frame(UUID(request.equipment_layer_id))
            except (ValueError, FileNotFoundError) as exc:
                raise ValueError("La couche importée est introuvable ou expirée.") from exc
        filosofi_path = (
            settings.filosofi_demo_path if request.territory_code == "62193" else None
        )
        if request.territory_code == "75056":
            filosofi_path = settings.filosofi_demo_path.with_name("paris-filosofi-200m.geojson")
        exclusion_path = (
            settings.water_mask_path if request.territory_code == "62193" else None
        )
        if request.territory_code == "75056":
            exclusion_path = settings.water_mask_path.with_name("paris-exclusion-mask.geojson")
        result = analyze_sites(
            request,
            settings.demo_data_path,
            filosofi_path,
            exclusion_path,
            settings.eligible_parcels_path,
            custom_facilities,
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
