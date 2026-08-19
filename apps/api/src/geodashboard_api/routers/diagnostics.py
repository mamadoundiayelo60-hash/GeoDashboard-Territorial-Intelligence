"""Diagnostics territoriaux guidés."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from geodashboard_api.io.layer_store import LayerStore
from geodashboard_api.models import CoverageRequest, CoverageResult
from geodashboard_api.routers.layers import layer_store
from geodashboard_api.services.coverage import CoverageError, analyze_coverage

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.post("/coverage", response_model=CoverageResult)
def coverage_diagnostic(
    request: CoverageRequest,
    store: Annotated[LayerStore, Depends(layer_store)],
) -> CoverageResult:
    """Calcule une couverture actuelle et un scénario comparable."""
    try:
        layer_id = UUID(request.layer_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Identifiant de couche invalide.") from exc
    try:
        frame = store.load_frame(layer_id)
        result = analyze_coverage(
            request.territory_geometry,
            frame,
            request.distance_m,
            request.population,
            request.scenario_locations,
        )
        store.record_event(
            "coverage_diagnostic",
            f"Couverture à {request.distance_m:.0f} m — {result.current.coverage_rate:.1f} %",
            {
                "layer_id": request.layer_id,
                "distance_m": request.distance_m,
                "scenario_locations": [item.model_dump() for item in request.scenario_locations],
                "current_rate": result.current.coverage_rate,
                "scenario_rate": result.scenario.coverage_rate,
            },
        )
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Couche introuvable.") from exc
    except CoverageError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
