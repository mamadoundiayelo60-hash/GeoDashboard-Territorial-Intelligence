"""Rapport PDF professionnel du moteur de décision TerriScope."""

from datetime import date
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from shapely.geometry import MultiPolygon, Point, Polygon, shape

from geodashboard_api.models import DecisionReportRequest

INK = colors.HexColor("#081225")
BLUE = colors.HexColor("#6F91F4")
TEAL = colors.HexColor("#28C6A8")
GOLD = colors.HexColor("#F4B83F")
PINK = colors.HexColor("#E45A78")
PALE = colors.HexColor("#F1F4F8")
MUTED = colors.HexColor("#5D687B")


def build_decision_report(request: DecisionReportRequest) -> bytes:
    """Construit une note paysage de deux pages, autonome et traçable."""
    buffer = BytesIO()
    doc = BaseDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=20 * mm,
        bottomMargin=16 * mm,
        title=request.title,
        author=request.author,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="decision")
    doc.addPageTemplates(PageTemplate(id="decision", frames=[frame], onPageEnd=_chrome))
    styles = _styles()
    story: list[Flowable] = [
        Paragraph("TERRISCOPE AI - NOTE DECISIONNELLE", styles["eyebrow"]),
        Paragraph(request.title, styles["title"]),
        Paragraph(
            f"{request.territory.name} - INSEE {request.territory.code} - "
            f"seuil {request.threshold_minutes} min - mode {_mode(request.mode)} - "
            f"généré le {date.today().strftime('%d/%m/%Y')}",
            styles["subtitle"],
        ),
        Spacer(1, 5 * mm),
        _metrics(request),
        Spacer(1, 5 * mm),
        Paragraph("Comparaison spatiale avant / après", styles["section"]),
        Spacer(1, 2 * mm),
        DecisionMaps(request, doc.width, 61 * mm),
        Spacer(1, 5 * mm),
        _recommendation(request, styles),
        PageBreak(),
        Paragraph("Parcelles alternatives", styles["section"]),
        Spacer(1, 2 * mm),
        _candidates(request),
        Spacer(1, 5 * mm),
        Paragraph("Sources, méthode et limites", styles["section"]),
        Spacer(1, 2 * mm),
        _traceability(request, styles),
    ]
    doc.build(story)
    return buffer.getvalue()


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "eyebrow": ParagraphStyle(
            "de",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            textColor=BLUE,
            tracking=1.4,
        ),
        "title": ParagraphStyle(
            "dt",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=24,
            textColor=INK,
            alignment=TA_LEFT,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "ds", parent=base["Normal"], fontSize=8, leading=11, textColor=MUTED
        ),
        "section": ParagraphStyle(
            "dh",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            textColor=INK,
        ),
        "body": ParagraphStyle(
            "db", parent=base["BodyText"], fontSize=7.5, leading=11, textColor=MUTED
        ),
        "white": ParagraphStyle(
            "dw",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=13,
            textColor=colors.white,
        ),
    }


def _metrics(request: DecisionReportRequest) -> Table:
    result = request.decision
    values = [
        ("ACCESSIBILITE ACTUELLE", f"{result.current_access_rate:.1f} %"),
        ("AVEC LA PARCELLE A", f"{result.scenario_access_rate:.1f} %"),
        ("HABITANTS SUPPLEMENTAIRES", f"+ {_number(result.gained_people)}"),
        ("SCORE MULTICRITERE", f"{result.recommendation.get('score', 0)}/100"),
    ]
    cells = [
        [
            Paragraph(
                f"<font size='6' color='#5D687B'>{label}</font><br/>"
                f"<font size='16'><b>{value}</b></font>"
            )
            for label, value in values
        ]
    ]
    table = Table(cells, colWidths=[None] * 4, rowHeights=[20 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D7DCE5")),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#D7DCE5")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return table


def _recommendation(request: DecisionReportRequest, styles: dict[str, ParagraphStyle]) -> Table:
    result = request.decision
    rec = result.recommendation
    parcel = rec.get("parcel_id") or "Non renseignée"
    area = _number(rec.get("parcel_area_m2"))
    zone = rec.get("planning_zone") or "A confirmer"
    explanation = str(rec.get("explanation", "")).replace("Le site A", "La parcelle A")
    content = f"<b>Parcelle {parcel}</b> - {area} m² - zonage {zone}<br/>{explanation}"
    table = Table(
        [[Paragraph("RECOMMANDATION N°1", styles["white"]), Paragraph(content, styles["white"])]],
        colWidths=[45 * mm, None],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), INK),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return table


def _candidates(request: DecisionReportRequest) -> Table:
    rows = [["Rang", "Parcelle", "Surface", "Zone GPU", "Score", "Gain habitants"]]
    for feature in request.decision.candidates.get("features", [])[:5]:
        prop = feature.get("properties", {})
        rows.append(
            [
                prop.get("rank"),
                prop.get("parcel_id") or "-",
                f"{_number(prop.get('parcel_area_m2'))} m²",
                prop.get("zone_label") or "-",
                f"{prop.get('score', 0)}/100",
                f"+ {_number(prop.get('gained_people'))}",
            ]
        )
    table = Table(rows, colWidths=[14 * mm, 42 * mm, 25 * mm, None, 25 * mm, 30 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), INK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D7DCE5")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _traceability(request: DecisionReportRequest, styles: dict[str, ParagraphStyle]) -> Table:
    sources = "<br/>".join(
        f"- {item['name']} : {item['provider']}" for item in request.decision.sources
    )
    limits = "<br/>".join(f"- {item}" for item in request.decision.limitations)
    weights = request.weights
    method = (
        f"{request.decision.method}<br/>Pondérations : population "
        f"{weights.population:.0%}, vulnérabilité {weights.vulnerability:.0%}, "
        f"équité {weights.equity:.0%}."
    )
    table = Table(
        [
            [
                Paragraph(f"<b>SOURCES</b><br/>{sources}", styles["body"]),
                Paragraph(
                    f"<b>METHODE</b><br/>{method}<br/><br/><b>LIMITES</b><br/>{limits}",
                    styles["body"],
                ),
            ]
        ],
        colWidths=[78 * mm, None],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#D7DCE5")),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


class DecisionMaps(Flowable):
    """Deux cartes vectorielles partageant la même emprise territoriale."""

    def __init__(self, request: DecisionReportRequest, width: float, height: float) -> None:
        super().__init__()
        self.request, self.width, self.height = request, width, height

    def draw(self) -> None:
        territory = shape(self.request.territory_geometry)
        areas = [
            shape(self.request.decision.current_service_area),
            shape(self.request.decision.scenario_service_area),
        ]
        gap = 7 * mm
        panel_width = (self.width - gap) / 2
        for index, (label, area, color) in enumerate(
            zip(["Situation actuelle", "Scénario recommandé"], areas, [BLUE, TEAL], strict=True)
        ):
            x = index * (panel_width + gap)
            self.canv.setFillColor(PALE)
            self.canv.roundRect(x, 0, panel_width, self.height, 4, fill=1, stroke=0)
            self.canv.setFillColor(INK)
            self.canv.setFont("Helvetica-Bold", 8)
            self.canv.drawString(x + 7, self.height - 13, label)
            self.canv.setFont("Helvetica-Bold", 6)
            self.canv.drawRightString(x + panel_width - 9, self.height - 13, "N ↑")
            _draw(
                self.canv,
                territory,
                territory.bounds,
                x + 7,
                7,
                panel_width - 14,
                self.height - 25,
                colors.HexColor("#E1E6ED"),
                colors.HexColor("#9CA7B6"),
            )
            _draw(
                self.canv,
                area,
                territory.bounds,
                x + 7,
                7,
                panel_width - 14,
                self.height - 25,
                color,
                color,
            )
            _draw_label(
                self.canv,
                self.request.territory.name,
                territory.centroid,
                territory.bounds,
                x + 7,
                7,
                panel_width - 14,
                self.height - 25,
            )
            self.canv.setFillColor(color)
            self.canv.rect(x + 10, 10, 5, 5, fill=1, stroke=0)
            self.canv.setFillColor(INK)
            self.canv.setFont("Helvetica", 5.5)
            self.canv.drawString(x + 18, 10.5, "Population accessible")
            if index == 1:
                candidates = self.request.decision.candidates.get("features", [])
                for feature in candidates[:3]:
                    _draw(
                        self.canv,
                        shape(feature["geometry"]),
                        territory.bounds,
                        x + 7,
                        7,
                        panel_width - 14,
                        self.height - 25,
                        GOLD,
                        INK,
                    )


def _draw(
    canvas: Any,
    geometry: Any,
    bounds: tuple[float, float, float, float],
    x: float,
    y: float,
    width: float,
    height: float,
    fill: Any,
    stroke: Any,
) -> None:
    min_x, min_y, max_x, max_y = bounds
    scale = min(width / max(max_x - min_x, 1e-9), height / max(max_y - min_y, 1e-9))
    ox = x + (width - (max_x - min_x) * scale) / 2
    oy = y + (height - (max_y - min_y) * scale) / 2
    if isinstance(geometry, Point):
        canvas.setFillColor(fill)
        canvas.setStrokeColor(stroke)
        canvas.circle(
            ox + (geometry.x - min_x) * scale,
            oy + (geometry.y - min_y) * scale,
            3,
            fill=1,
            stroke=1,
        )
        return
    polygons = (
        [geometry]
        if isinstance(geometry, Polygon)
        else list(geometry.geoms)
        if isinstance(geometry, MultiPolygon)
        else []
    )
    canvas.setFillColor(fill)
    canvas.setStrokeColor(stroke)
    for polygon in polygons:
        coordinates = list(polygon.exterior.coords)
        if not coordinates:
            continue
        path = canvas.beginPath()
        path.moveTo(
            ox + (coordinates[0][0] - min_x) * scale, oy + (coordinates[0][1] - min_y) * scale
        )
        for px, py in coordinates[1:]:
            path.lineTo(ox + (px - min_x) * scale, oy + (py - min_y) * scale)
        path.close()
        canvas.drawPath(path, fill=1, stroke=1)


def _draw_label(
    canvas: Any,
    text: str,
    point: Point,
    bounds: tuple[float, float, float, float],
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
    min_x, min_y, max_x, max_y = bounds
    scale = min(width / max(max_x - min_x, 1e-9), height / max(max_y - min_y, 1e-9))
    ox = x + (width - (max_x - min_x) * scale) / 2
    oy = y + (height - (max_y - min_y) * scale) / 2
    canvas.setFillColor(colors.HexColor("#3D4A5F"))
    canvas.setFont("Helvetica-Bold", 6)
    canvas.drawCentredString(
        ox + (point.x - min_x) * scale,
        oy + (point.y - min_y) * scale,
        text,
    )


def _chrome(canvas: Any, doc: BaseDocTemplate) -> None:
    canvas.saveState()
    width, height = doc.pagesize
    canvas.setFillColor(INK)
    canvas.rect(0, height - 9 * mm, width, 9 * mm, fill=1, stroke=0)
    canvas.setFillColor(TEAL)
    canvas.circle(17 * mm, height - 4.5 * mm, 2 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawString(22 * mm, height - 5.5 * mm, "TERRISCOPE AI - SPATIAL DECISION INTELLIGENCE")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 6.5)
    canvas.drawString(
        16 * mm,
        7 * mm,
        f"Préqualification automatique - validation requise - {date.today():%d/%m/%Y}",
    )
    canvas.drawRightString(width - 16 * mm, 7 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _mode(value: str) -> str:
    return {"pedestrian": "à pied", "bicycle": "vélo", "car": "voiture"}.get(value, value)


def _number(value: Any) -> str:
    return f"{int(value):,}".replace(",", " ") if value is not None else "-"
