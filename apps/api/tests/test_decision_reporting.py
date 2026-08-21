from io import BytesIO

from pypdf import PdfReader

from geodashboard_api.models import DecisionReportRequest
from geodashboard_api.services.decision_reporting import build_decision_report


def _request() -> DecisionReportRequest:
    territory = {
        "type": "Polygon",
        "coordinates": [[[1.8, 50.9], [1.95, 50.9], [1.95, 51.0], [1.8, 51.0], [1.8, 50.9]]],
    }
    area = {
        "type": "Polygon",
        "coordinates": [[[1.82, 50.92], [1.9, 50.92], [1.9, 50.98], [1.82, 50.98], [1.82, 50.92]]],
    }
    candidate = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [1.91, 50.96]},
        "properties": {
            "rank": 1,
            "score": 96.4,
            "gained_people": 1480,
            "parcel_id": "62193000AB0123",
            "parcel_area_m2": 2450,
            "zone_label": "U",
        },
    }
    return DecisionReportRequest.model_validate(
        {
            "territory": {
                "name": "Calais",
                "code": "62193",
                "area_km2": 33.5,
                "population": 67544,
            },
            "territory_geometry": territory,
            "mode": "pedestrian",
            "threshold_minutes": 15,
            "weights": {"population": 0.45, "vulnerability": 0.35, "equity": 0.2},
            "decision": {
                "method": "Isochrones IGN et classement multicritère",
                "data_status": "Données réelles",
                "current_access_rate": 83.0,
                "scenario_access_rate": 86.2,
                "gained_people": 1480,
                "underserved_people": 11000,
                "equity_gain": 3.2,
                "facilities": {"type": "FeatureCollection", "features": []},
                "demand_grid": {"type": "FeatureCollection", "features": []},
                "candidates": {"type": "FeatureCollection", "features": [candidate]},
                "current_service_area": area,
                "scenario_service_area": territory,
                "recommendation": {
                    "rank": 1,
                    "score": 96.4,
                    "gained_people": 1480,
                    "parcel_id": "62193000AB0123",
                    "parcel_area_m2": 2450,
                    "planning_zone": "U",
                    "explanation": "Cette parcelle maximise l'accessibilité.",
                },
                "sources": [{"name": "Parcelles", "provider": "Cadastre Etalab"}],
                "limitations": ["Une instruction d'urbanisme reste nécessaire."],
            },
        }
    )


def test_decision_report_is_a_readable_multipage_pdf() -> None:
    content = build_decision_report(_request())
    reader = PdfReader(BytesIO(content))

    assert content.startswith(b"%PDF")
    assert len(reader.pages) >= 2
    text = "".join(page.extract_text() or "" for page in reader.pages)
    assert "62193000AB0123" in text
    assert "Cadastre Etalab" in text
