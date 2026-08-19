"""Génère le rapport PDF d'exemple inclus dans le dépôt."""

from pathlib import Path

from geodashboard_api.models import ReportRequest
from geodashboard_api.services.reporting import build_report

ROOT = Path(__file__).resolve().parents[1]
REQUEST_PATH = ROOT / "data" / "demo" / "report_request.json"
OUTPUT_PATH = ROOT / "output" / "pdf" / "geodashboard-example-report.pdf"


def main() -> None:
    """Valide la requête de démonstration et écrit le PDF stable."""
    request = ReportRequest.model_validate_json(
        REQUEST_PATH.read_text(encoding="utf-8")
    )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_bytes(build_report(request))
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
