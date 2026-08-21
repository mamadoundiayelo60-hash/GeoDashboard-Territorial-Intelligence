"""Rapports et exports documentés de la session."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse

from geodashboard_api.io.layer_store import LayerStore
from geodashboard_api.models import DecisionReportRequest, ReportRequest
from geodashboard_api.routers.layers import layer_store
from geodashboard_api.services.decision_reporting import build_decision_report
from geodashboard_api.services.reporting import build_report

router = APIRouter(prefix="/restitution", tags=["restitution"])


@router.post("/decision-reports", response_class=Response)
def decision_report(request: DecisionReportRequest) -> Response:
    """Génère la note PDF du scénario d'implantation TerriScope."""
    return Response(
        content=build_decision_report(request),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="terriscope-decision-report.pdf"'},
    )


@router.post("/reports", response_class=Response)
def report(
    request: ReportRequest,
    store: Annotated[LayerStore, Depends(layer_store)],
) -> Response:
    """Génère un rapport PDF selon un modèle maîtrisé."""
    content = build_report(request)
    store.record_event(
        "report_generated",
        f"Rapport {request.template.value} généré pour {request.territory.name}",
        {
            "template": request.template.value,
            "territory_code": request.territory.code,
            "source_layer_name": request.source_layer_name,
        },
    )
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="geodashboard-report.pdf"'},
    )


@router.get("/layers/{layer_id}", response_class=Response)
def export_layer(
    layer_id: UUID,
    store: Annotated[LayerStore, Depends(layer_store)],
    output_format: Annotated[str, Query(alias="format", pattern="^(geojson|gpkg)$")] = "geojson",
) -> Response:
    """Exporte une couche canonique dans un format SIG interopérable."""
    try:
        frame = store.load_frame(layer_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Couche introuvable.") from exc
    if output_format == "geojson":
        content = frame.to_json(drop_id=True).encode()
        media_type = "application/geo+json"
        suffix = "geojson"
    else:
        with TemporaryDirectory(prefix="geodashboard-export-") as directory:
            path = Path(directory) / "export.gpkg"
            frame.to_file(path, driver="GPKG", layer="resultat")
            content = path.read_bytes()
        media_type = "application/geopackage+sqlite3"
        suffix = "gpkg"
    store.record_event(
        "layer_export",
        f"Couche exportée au format {output_format.upper()}",
        {"layer_id": str(layer_id), "format": output_format},
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="layer-{layer_id}.{suffix}"'},
    )


@router.get("/manifest", response_class=JSONResponse)
def manifest(store: Annotated[LayerStore, Depends(layer_store)]) -> JSONResponse:
    """Produit un manifeste JSON reproductible sans données sensibles."""
    payload = {
        "schema_version": "1.0",
        "generator": "GeoDashboard Territorial Intelligence Studio",
        "layers": [layer.model_dump(exclude={"preview"}) for layer in store.list()],
        "history": [event.model_dump() for event in reversed(store.history())],
    }
    return JSONResponse(
        content=json.loads(json.dumps(payload, default=str)),
        headers={"Content-Disposition": 'attachment; filename="geodashboard-manifest.json"'},
    )
