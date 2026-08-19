"""Tests des frontières de sécurité des imports."""

from pathlib import Path
from zipfile import ZipFile

import pytest

from geodashboard_api.io.secure_upload import UploadValidationError, read_vector


def test_zip_slip_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "hostile.zip"
    with ZipFile(archive, "w") as output:
        output.writestr("../escape.shp", b"not-a-shapefile")
    with pytest.raises(UploadValidationError, match="chemin dangereux"):
        read_vector(archive, extraction_dir=tmp_path / "extract")


def test_geojson_without_crs_requires_declaration(tmp_path: Path) -> None:
    path = tmp_path / "layer.geojson"
    path.write_text(
        '{"type":"FeatureCollection","features":[]}',
        encoding="utf-8",
    )
    with pytest.raises(UploadValidationError):
        read_vector(path, extraction_dir=tmp_path / "extract")
