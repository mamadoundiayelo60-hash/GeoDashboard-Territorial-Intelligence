"""Contrôles de qualité explicables appliqués aux couches."""

import geopandas as gpd

from geodashboard_api.models import QualityReport


def assess_quality(frame: gpd.GeoDataFrame) -> QualityReport:
    """Calcule un score informatif sans corriger silencieusement les données."""
    invalid = int((~frame.geometry.is_valid & ~frame.geometry.isna()).sum())
    empty = int(frame.geometry.is_empty.sum() + frame.geometry.isna().sum())
    duplicates = int(frame.geometry.duplicated().sum())
    attributes = frame.drop(columns=frame.geometry.name)
    null_cells = int(attributes.isna().sum().sum())
    warnings: list[str] = []
    if invalid:
        warnings.append(f"{invalid} géométrie(s) invalide(s)")
    if empty:
        warnings.append(f"{empty} géométrie(s) vide(s) ou absente(s)")
    if duplicates:
        warnings.append(f"{duplicates} géométrie(s) dupliquée(s)")
    if null_cells:
        warnings.append(f"{null_cells} valeur(s) attributaire(s) manquante(s)")
    penalty = min(100, invalid * 8 + empty * 10 + duplicates * 2 + min(25, null_cells))
    return QualityReport(
        score=max(0, 100 - penalty),
        invalid_geometries=invalid,
        empty_geometries=empty,
        duplicate_geometries=duplicates,
        null_cells=null_cells,
        warnings=warnings,
    )
