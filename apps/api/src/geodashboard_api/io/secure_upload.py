"""Lecture multi-format avec limites et extraction ZIP défensive."""

import json
import shutil
import stat
from pathlib import Path, PurePosixPath
from typing import cast
from zipfile import BadZipFile, ZipFile

import geopandas as gpd
import pandas as pd
import shapely
from fastapi import UploadFile

ALLOWED_SUFFIXES = {".geojson", ".json", ".gpkg", ".zip", ".kml", ".csv"}
MAX_ARCHIVE_FILES = 30
MAX_UNCOMPRESSED_BYTES = 250 * 1024 * 1024
MAX_FEATURES = 100_000
MAX_COORDINATES = 2_000_000


class UploadValidationError(ValueError):
    """Erreur de fichier formulée pour l'utilisateur."""


async def save_bounded_upload(upload: UploadFile, destination: Path, max_bytes: int) -> Path:
    """Copie par blocs et interrompt l'écriture au-delà de la limite."""
    size = 0
    with destination.open("wb") as target:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                target.close()
                destination.unlink(missing_ok=True)
                raise UploadValidationError("Le fichier dépasse la taille autorisée.")
            target.write(chunk)
    if size == 0:
        raise UploadValidationError("Le fichier envoyé est vide.")
    return destination


def read_vector(
    path: Path,
    *,
    extraction_dir: Path,
    source_crs: str | None = None,
    longitude_field: str | None = None,
    latitude_field: str | None = None,
) -> tuple[gpd.GeoDataFrame, str]:
    """Lit un format autorisé puis applique les limites de complexité."""
    suffix = path.suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise UploadValidationError("Format non autorisé.")
    _validate_signature(path, suffix)
    source_path = path
    source_format = suffix.lstrip(".")
    if suffix == ".zip":
        source_path = _extract_shapefile(path, extraction_dir)
        source_format = "shapefile"
    if suffix == ".csv":
        frame = _read_csv(path, longitude_field, latitude_field, source_crs)
    else:
        if suffix == ".kml":
            _reject_active_xml(path)
        frame = gpd.read_file(source_path, engine="pyogrio")
        if frame.crs is None and source_crs:
            frame = frame.set_crs(source_crs)
    if len(frame) > MAX_FEATURES:
        raise UploadValidationError(f"La couche dépasse {MAX_FEATURES:,} entités.")
    if frame.crs is None:
        raise UploadValidationError("Le CRS est absent : indiquez le CRS source avant l'import.")
    if frame.geometry.name not in frame or frame.geometry.isna().all():
        raise UploadValidationError("Aucune géométrie exploitable n'a été détectée.")
    coordinate_count = int(shapely.count_coordinates(frame.geometry.array))
    if coordinate_count > MAX_COORDINATES:
        raise UploadValidationError("La géométrie est trop complexe pour une session web.")
    return frame, source_format


def _read_csv(
    path: Path,
    longitude_field: str | None,
    latitude_field: str | None,
    source_crs: str | None,
) -> gpd.GeoDataFrame:
    table = pd.read_csv(path, nrows=MAX_FEATURES + 1)
    lon = longitude_field or _find_column(table, {"longitude", "lon", "lng", "x"})
    lat = latitude_field or _find_column(table, {"latitude", "lat", "y"})
    if not lon or not lat or lon not in table or lat not in table:
        raise UploadValidationError("Choisissez les colonnes longitude et latitude du CSV.")
    geometry = gpd.points_from_xy(table[lon], table[lat])
    return gpd.GeoDataFrame(table, geometry=geometry, crs=source_crs or "EPSG:4326")


def _find_column(table: pd.DataFrame, candidates: set[str]) -> str | None:
    return next((str(column) for column in table if str(column).casefold() in candidates), None)


def _extract_shapefile(archive_path: Path, destination: Path) -> Path:
    try:
        with ZipFile(archive_path) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_ARCHIVE_FILES:
                raise UploadValidationError("L'archive contient trop de fichiers.")
            if sum(entry.file_size for entry in entries) > MAX_UNCOMPRESSED_BYTES:
                raise UploadValidationError("L'archive décompressée est trop volumineuse.")
            for entry in entries:
                normalized = PurePosixPath(entry.filename.replace("\\", "/"))
                if normalized.is_absolute() or ".." in normalized.parts:
                    raise UploadValidationError("L'archive contient un chemin dangereux.")
                if stat.S_ISLNK(entry.external_attr >> 16):
                    raise UploadValidationError("Les liens symboliques sont refusés.")
            destination.mkdir(parents=True, exist_ok=True)
            for entry in entries:
                normalized = PurePosixPath(entry.filename.replace("\\", "/"))
                target = destination.joinpath(*normalized.parts)
                if entry.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
    except BadZipFile as exc:
        raise UploadValidationError("L'archive ZIP est illisible.") from exc
    shapefiles = list(destination.rglob("*.shp"))
    if len(shapefiles) != 1:
        raise UploadValidationError("L'archive doit contenir exactement un Shapefile.")
    stem = shapefiles[0].with_suffix("")
    missing = [suffix for suffix in (".shx", ".dbf") if not stem.with_suffix(suffix).exists()]
    if missing:
        raise UploadValidationError(f"Composants Shapefile manquants : {', '.join(missing)}.")
    return shapefiles[0]


def _validate_signature(path: Path, suffix: str) -> None:
    head = path.read_bytes()[:64].lstrip()
    valid = {
        ".zip": head.startswith(b"PK"),
        ".gpkg": head.startswith(b"SQLite format 3"),
        ".geojson": head.startswith((b"{", b"[")),
        ".json": head.startswith((b"{", b"[")),
        ".kml": head.startswith(b"<") or head.startswith(b"<?xml"),
        ".csv": b"\x00" not in head,
    }[suffix]
    if not valid:
        raise UploadValidationError("Le contenu du fichier ne correspond pas à son extension.")


def _reject_active_xml(path: Path) -> None:
    text = path.read_bytes()[:1_000_000].upper()
    if b"<!DOCTYPE" in text or b"<!ENTITY" in text:
        raise UploadValidationError("Les déclarations XML actives sont refusées dans un KML.")


def feature_collection(frame: gpd.GeoDataFrame, limit: int = 1_000) -> dict[str, object]:
    """Produit un aperçu WGS84 borné et sérialisable."""
    preview = frame.head(limit).to_crs(4326)
    return cast(dict[str, object], json.loads(preview.to_json(drop_id=True)))
