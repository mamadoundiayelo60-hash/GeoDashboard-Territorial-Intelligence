"""Tests du rapport décisionnel PDF."""

from pypdf import PdfReader

from geodashboard_api.models import ReportRequest
from geodashboard_api.services.reporting import build_report


def report_payload() -> dict[str, object]:
    return {
        "title": "Accès aux équipements de proximité",
        "template": "a4_portrait",
        "territory": {"name": "Calais", "code": "62193", "area_km2": 33.5, "population": 67_544},
        "source_layer_name": "Équipements de démonstration",
        "author": "Mamadou Ndiaye LO",
        "diagnostic": {
            "method": "Buffer euclidien intersecté au territoire",
            "distance_m": 500,
            "current": {
                "equipment_count": 8,
                "covered_area_km2": 18.2,
                "uncovered_area_km2": 15.3,
                "coverage_rate": 54.3,
                "estimated_covered_population": 36_681,
            },
            "scenario": {
                "equipment_count": 10,
                "covered_area_km2": 25.1,
                "uncovered_area_km2": 8.4,
                "coverage_rate": 74.9,
                "estimated_covered_population": 50_593,
            },
            "gain_points": 20.6,
            "covered_geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[1.84, 50.94], [1.86, 50.94], [1.86, 50.96], [1.84, 50.96], [1.84, 50.94]]
                ],
            },
            "uncovered_geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[1.83, 50.93], [1.88, 50.93], [1.88, 50.97], [1.83, 50.97], [1.83, 50.93]]
                ],
            },
            "scenario_covered_geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [1.835, 50.935],
                        [1.87, 50.935],
                        [1.87, 50.965],
                        [1.835, 50.965],
                        [1.835, 50.935],
                    ]
                ],
            },
            "scenario_uncovered_geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[1.83, 50.93], [1.88, 50.93], [1.88, 50.97], [1.83, 50.97], [1.83, 50.93]]
                ],
            },
            "interpretation": "Le scénario améliore nettement la couverture de 20,6 points.",
            "warnings": ["Couverture géométrique uniquement."],
        },
    }


def test_pdf_is_readable_and_contains_key_sections(tmp_path) -> None:  # type: ignore[no-untyped-def]
    content = build_report(ReportRequest.model_validate(report_payload()))
    path = tmp_path / "report.pdf"
    path.write_bytes(content)
    reader = PdfReader(path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert len(reader.pages) >= 1
    assert "GEODASHBOARD" in text
    assert "Indicateurs detailles" in text
    assert "20.6 points" in text
