"""API du studio de décision territoriale V2."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from geodashboard_api.config import Settings, get_settings
from geodashboard_api.models import DecisionRequest, DecisionResult
from geodashboard_api.services.site_selection import analyze_sites

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.post("/site-selection", response_model=DecisionResult)
def site_selection(
    request: DecisionRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> DecisionResult:
    """Produit un diagnostic et cinq sites candidats explicables."""
    try:
        return analyze_sites(request, settings.demo_data_path)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
