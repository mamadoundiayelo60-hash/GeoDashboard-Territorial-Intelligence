"""Atelier expert : expressions, SQL contrôlé et historique."""

from typing import Annotated, Any
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from geodashboard_api.config import Settings, get_settings
from geodashboard_api.io.layer_store import LayerStore
from geodashboard_api.io.quality import assess_quality
from geodashboard_api.io.secure_upload import feature_collection
from geodashboard_api.models import (
    CalculatedFieldRequest,
    CalculatedFieldResult,
    HistoryEvent,
    SqlQueryRequest,
    SqlQueryResult,
)
from geodashboard_api.routers.layers import layer_store
from geodashboard_api.services.expressions import ExpressionError, calculate
from geodashboard_api.services.sql_guard import SqlGuardError, validate_read_only_sql
from geodashboard_api.services.sql_runner import SqlExecutionError, execute_read_only

router = APIRouter(prefix="/expert", tags=["expert"])


@router.post("/calculated-fields", response_model=CalculatedFieldResult)
def calculated_field(
    request: CalculatedFieldRequest,
    store: Annotated[LayerStore, Depends(layer_store)],
) -> CalculatedFieldResult:
    """Ajoute un champ calculé sans évaluer de code Python arbitraire."""
    try:
        identifier = UUID(request.layer_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Identifiant de couche invalide.") from exc
    try:
        frame = store.load_frame(identifier)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Couche introuvable.") from exc
    if request.field_name in frame.columns:
        raise HTTPException(status_code=409, detail="Ce nom de champ existe déjà.")
    try:
        values = calculate(request.expression, frame)
    except ExpressionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    frame[request.field_name] = values
    layer = next(item for item in store.list() if item.id == request.layer_id)
    layer.field_count = len(frame.columns) - 1
    layer.quality = assess_quality(frame)
    layer.preview = feature_collection(frame)
    store.save(layer, frame)
    store.record_event(
        "calculated_field",
        f"Champ {request.field_name} ajouté à {layer.name}",
        {
            "layer_id": request.layer_id,
            "field_name": request.field_name,
            "expression": request.expression,
        },
    )
    preview: list[Any] = [None if pd.isna(value) else value for value in values.head(10).tolist()]
    return CalculatedFieldResult(layer=layer, field_name=request.field_name, preview=preview)


@router.post("/sql", response_model=SqlQueryResult)
def sql_query(
    request: SqlQueryRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[LayerStore, Depends(layer_store)],
) -> SqlQueryResult:
    """Exécute une lecture bornée sur les seules vues publiées."""
    try:
        validated = validate_read_only_sql(request.query)
        result = execute_read_only(settings.database_url, validated)
    except (SqlGuardError, SqlExecutionError) as exc:
        status_code = 422 if isinstance(exc, SqlGuardError) else 503
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    store.record_event(
        "sql_query",
        f"Requête experte exécutée — {result.row_count} lignes",
        {"query": request.query, "duration_ms": result.duration_ms, "row_count": result.row_count},
    )
    return result


@router.get("/history", response_model=list[HistoryEvent])
def history(store: Annotated[LayerStore, Depends(layer_store)]) -> list[HistoryEvent]:
    """Expose le manifeste chronologique de la session."""
    return store.history()
