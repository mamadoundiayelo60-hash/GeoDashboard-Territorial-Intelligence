"""Import et catalogue de couches isolés par session."""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile, status

from geodashboard_api.config import Settings, get_settings
from geodashboard_api.io.layer_store import LayerStore
from geodashboard_api.io.quality import assess_quality
from geodashboard_api.io.secure_upload import (
    ALLOWED_SUFFIXES,
    UploadValidationError,
    feature_collection,
    read_vector,
    save_bounded_upload,
)
from geodashboard_api.models import LayerSummary

router = APIRouter(prefix="/layers", tags=["layers"])


def session_id(x_session_id: Annotated[str, Header()]) -> UUID:
    """Exige un identifiant non prédictible sans accepter un chemin libre."""
    try:
        return UUID(x_session_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Identifiant de session invalide.") from exc


def layer_store(
    identifier: Annotated[UUID, Depends(session_id)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LayerStore:
    return LayerStore(settings.runtime_data_dir, identifier)


@router.get("", response_model=list[LayerSummary])
def list_layers(store: Annotated[LayerStore, Depends(layer_store)]) -> list[LayerSummary]:
    """Retourne le catalogue de la session courante."""
    return store.list()


@router.post("/demo", response_model=LayerSummary, status_code=status.HTTP_201_CREATED)
def load_demo_layer(
    store: Annotated[LayerStore, Depends(layer_store)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LayerSummary:
    """Charge le jeu OSM prévalidé sans dépendre d'un service distant au clic."""
    if not settings.demo_data_path.is_file():
        raise HTTPException(status_code=503, detail="Le jeu de démonstration est indisponible.")
    existing = next((layer for layer in store.list() if layer.source_format == "demo_osm"), None)
    if existing:
        return existing
    frame, _ = read_vector(
        settings.demo_data_path,
        extraction_dir=settings.runtime_data_dir / "unused-demo-extraction",
    )
    layer_id = uuid4()
    layer = LayerSummary(
        id=str(layer_id),
        name="Équipements de proximité - Calais",
        source_format="demo_osm",
        feature_count=len(frame),
        field_count=len(frame.columns) - 1,
        geometry_types=sorted(str(value) for value in frame.geometry.geom_type.unique()),
        crs=frame.crs.to_string(),
        quality=assess_quality(frame),
        preview=feature_collection(frame),
    )
    store.save(layer, frame)
    store.record_event(
        "demo_loaded",
        f"Démonstration OSM chargée - {layer.feature_count} équipements",
        {"layer_id": layer.id, "source": "OpenStreetMap", "license": "ODbL 1.0"},
    )
    return layer


@router.post("/upload", response_model=LayerSummary, status_code=status.HTTP_201_CREATED)
async def upload_layer(
    store: Annotated[LayerStore, Depends(layer_store)],
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File()],
    source_crs: Annotated[str | None, Query(max_length=32)] = None,
    longitude_field: Annotated[str | None, Query(max_length=80)] = None,
    latitude_field: Annotated[str | None, Query(max_length=80)] = None,
) -> LayerSummary:
    """Valide, normalise et ajoute une couche au catalogue."""
    original_name = Path(file.filename or "layer").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail="Format de fichier non autorisé.")
    layer_id = uuid4()
    try:
        with TemporaryDirectory(prefix="geodashboard-upload-") as temp:
            temp_dir = Path(temp)
            uploaded = await save_bounded_upload(
                file, temp_dir / f"input{suffix}", settings.max_upload_mb * 1024 * 1024
            )
            frame, source_format = read_vector(
                uploaded,
                extraction_dir=temp_dir / "extracted",
                source_crs=source_crs,
                longitude_field=longitude_field,
                latitude_field=latitude_field,
            )
            quality = assess_quality(frame)
            layer = LayerSummary(
                id=str(layer_id),
                name=Path(original_name).stem[:120],
                source_format=source_format,
                feature_count=len(frame),
                field_count=len(frame.columns) - 1,
                geometry_types=sorted(str(value) for value in frame.geometry.geom_type.unique()),
                crs=frame.crs.to_string(),
                quality=quality,
                preview=feature_collection(frame),
            )
            store.save(layer, frame)
            store.record_event(
                "layer_import",
                f"Couche {layer.name} importée — {layer.feature_count} entités",
                {
                    "layer_id": layer.id,
                    "source_format": layer.source_format,
                    "quality_score": layer.quality.score,
                },
            )
            return layer
    except UploadValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail="La couche n'a pas pu être lue.") from exc
    finally:
        await file.close()


@router.delete("/{layer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_layer(
    layer_id: UUID,
    store: Annotated[LayerStore, Depends(layer_store)],
) -> None:
    """Retire une couche de la session sans accepter de chemin utilisateur."""
    if not store.delete(layer_id):
        raise HTTPException(status_code=404, detail="Couche introuvable.")
    store.record_event(
        "layer_delete",
        "Couche retirée de la session",
        {"layer_id": str(layer_id)},
    )
