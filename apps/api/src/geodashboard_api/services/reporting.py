"""Rapports décisionnels vectoriels générés côté serveur."""

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.geometry.base import BaseGeometry

from geodashboard_api.models import ReportRequest, ReportTemplate

INK = colors.HexColor("#182033")
PURPLE = colors.HexColor("#7452C8")
TEAL = colors.HexColor("#0D8B80")
GOLD = colors.HexColor("#F6B73C")
PALE = colors.HexColor("#F2F3F7")
MUTED = colors.HexColor("#677083")


def build_report(request: ReportRequest) -> bytes:
    """Construit un PDF paginé avec carte vectorielle et indicateurs."""
    buffer = BytesIO()
    page_size = _page_size(request.template)
    doc = BaseDocTemplate(
        buffer,
        pagesize=page_size,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=24 * mm,
        bottomMargin=18 * mm,
        title=request.title,
        author=request.author,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="content")
    doc.addPageTemplates(PageTemplate(id="report", frames=[frame], onPageEnd=_page_chrome))
    styles = _styles()
    diagnostic = request.diagnostic
    story: list[Flowable] = [
        Paragraph("GEODASHBOARD - NOTE DECISIONNELLE", styles["eyebrow"]),
        Paragraph(request.title, styles["title"]),
        Paragraph(
            f"{request.territory.name} - Code INSEE {request.territory.code} - "
            f"Analyse du potentiel de desserte a {diagnostic.distance_m:.0f} metres",
            styles["subtitle"],
        ),
        Spacer(1, 7 * mm),
        _metric_table(request),
        Spacer(1, 7 * mm),
        KeepTogether(
            [
                Paragraph("Lecture spatiale : situation actuelle et scenario", styles["section"]),
                Spacer(1, 3 * mm),
                CoverageMaps(request, width=doc.width, height=67 * mm),
            ]
        ),
        Spacer(1, 7 * mm),
        _decision_block(request, styles),
        Spacer(1, 6 * mm),
    ]
    if request.include_details:
        story.extend(
            [
                Paragraph("Indicateurs detailles", styles["section"]),
                Spacer(1, 2 * mm),
                _detail_table(request),
                Spacer(1, 6 * mm),
            ]
        )
    if request.include_methodology:
        methodology: list[Flowable] = [
            Paragraph("Methode, limites et tracabilite", styles["section"]),
            Paragraph(
                "La couverture representee est un buffer euclidien intersecte avec la limite "
                "communale. Elle ne doit pas etre interpretee comme un temps de trajet ou une "
                "distance de reseau. L'estimation de population est proportionnelle a la "
                "surface couverte et doit etre remplacee par une grille carroyée pour une "
                "etude operationnelle.",
                styles["body"],
            ),
        ]
        if request.include_sources:
            methodology.append(_source_table(request))
        story.append(KeepTogether(methodology))
    elif request.include_sources:
        story.append(_source_table(request))
    doc.build(story)
    return buffer.getvalue()


def _page_size(template: ReportTemplate) -> tuple[float, float]:
    if template == ReportTemplate.A3_LANDSCAPE:
        return landscape(A3)
    if template == ReportTemplate.A4_LANDSCAPE:
        return landscape(A4)
    return A4


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "eyebrow": ParagraphStyle(
            "eyebrow",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=PURPLE,
            spaceAfter=4,
            tracking=1.4,
        ),
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=23,
            leading=26,
            alignment=TA_LEFT,
            textColor=INK,
            spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"], fontSize=9, leading=13, textColor=MUTED
        ),
        "section": ParagraphStyle(
            "section",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=INK,
        ),
        "body": ParagraphStyle(
            "body", parent=base["BodyText"], fontSize=8, leading=12, textColor=MUTED, spaceAfter=6
        ),
        "decision": ParagraphStyle(
            "decision",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=colors.white,
        ),
    }


def _metric_table(request: ReportRequest) -> Table:
    current = request.diagnostic.current
    scenario = request.diagnostic.scenario
    values = [
        ("COUVERTURE ACTUELLE", f"{current.coverage_rate:.1f} %"),
        ("COUVERTURE SCENARIO", f"{scenario.coverage_rate:.1f} %"),
        ("GAIN", f"+ {request.diagnostic.gain_points:.1f} points"),
        ("EQUIPEMENTS", f"{current.equipment_count} -> {scenario.equipment_count}"),
    ]
    cells = [
        [
            Paragraph(
                f"<font size='7' color='#677083'>{label}</font><br/>"
                f"<font size='17'><b>{value}</b></font>"
            )
            for label, value in values
        ]
    ]
    table = Table(cells, colWidths=[None] * 4, rowHeights=[23 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8DBE4")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8DBE4")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return table


def _decision_block(request: ReportRequest, styles: dict[str, ParagraphStyle]) -> Table:
    text = request.diagnostic.interpretation
    table = Table(
        [
            [
                Paragraph(
                    "LECTURE DECISIONNELLE",
                    ParagraphStyle(
                        "small-white",
                        fontName="Helvetica-Bold",
                        fontSize=7,
                        textColor=colors.HexColor("#A7EEE5"),
                    ),
                ),
                Paragraph(text, styles["decision"]),
            ]
        ],
        colWidths=[38 * mm, None],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), TEAL),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 11),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
                ("LEFTPADDING", (0, 0), (-1, -1), 11),
                ("RIGHTPADDING", (0, 0), (-1, -1), 11),
            ]
        )
    )
    return table


def _detail_table(request: ReportRequest) -> Table:
    current, scenario = request.diagnostic.current, request.diagnostic.scenario
    rows = [
        ["Indicateur", "Situation actuelle", "Scenario"],
        [
            "Surface couverte",
            f"{current.covered_area_km2:.3f} km2",
            f"{scenario.covered_area_km2:.3f} km2",
        ],
        [
            "Surface non couverte",
            f"{current.uncovered_area_km2:.3f} km2",
            f"{scenario.uncovered_area_km2:.3f} km2",
        ],
        [
            "Population potentiellement couverte",
            _number(current.estimated_covered_population),
            _number(scenario.estimated_covered_population),
        ],
        ["Taux de couverture", f"{current.coverage_rate:.2f} %", f"{scenario.coverage_rate:.2f} %"],
    ]
    table = Table(rows, colWidths=[None, 40 * mm, 40 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), INK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8DBE4")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def _source_table(request: ReportRequest) -> Table:
    rows = [
        ["Couche source", request.source_layer_name],
        ["Territoire", f"{request.territory.name} ({request.territory.code})"],
        ["Methode", request.diagnostic.method],
        ["Auteur", request.author],
    ]
    table = Table(rows, colWidths=[32 * mm, None])
    table.setStyle(
        TableStyle(
            [
                ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#E1E3E9")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _number(value: int | None) -> str:
    return f"{value:,}".replace(",", " ") if value is not None else "Non disponible"


def _page_chrome(canvas: Any, doc: BaseDocTemplate) -> None:
    canvas.saveState()
    width, height = doc.pagesize
    canvas.setFillColor(INK)
    canvas.rect(0, height - 10 * mm, width, 10 * mm, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(18 * mm, height - 7 * mm, 4 * mm, 4 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawString(24 * mm, height - 6.2 * mm, "GEODASHBOARD TERRITORIAL INTELLIGENCE")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(
        18 * mm, 9 * mm, "Rapport genere automatiquement - resultat a valider par un expert"
    )
    canvas.drawRightString(width - 18 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


class CoverageMaps(Flowable):
    """Deux mini-cartes vectorielles partageant la meme emprise."""

    def __init__(self, request: ReportRequest, width: float, height: float) -> None:
        super().__init__()
        self.request = request
        self.width = width
        self.height = height

    def draw(self) -> None:
        gap = 8 * mm
        panel_width = (self.width - gap) / 2
        geometries = [
            shape(self.request.diagnostic.covered_geometry),
            shape(self.request.diagnostic.scenario_covered_geometry),
        ]
        territory = shape(self.request.diagnostic.scenario_uncovered_geometry).union(geometries[1])
        for index, (label, geometry, color) in enumerate(
            zip(["Situation actuelle", "Scenario teste"], geometries, [PURPLE, TEAL], strict=True)
        ):
            x = index * (panel_width + gap)
            self.canv.setFillColor(PALE)
            self.canv.roundRect(x, 0, panel_width, self.height, 5, fill=1, stroke=0)
            self.canv.setFillColor(INK)
            self.canv.setFont("Helvetica-Bold", 8)
            self.canv.drawString(x + 8, self.height - 14, label)
            _draw_geometry(
                self.canv,
                territory,
                territory.bounds,
                x + 8,
                8,
                panel_width - 16,
                self.height - 28,
                colors.HexColor("#DDE1E8"),
                colors.HexColor("#A5ACB9"),
            )
            _draw_geometry(
                self.canv,
                geometry,
                territory.bounds,
                x + 8,
                8,
                panel_width - 16,
                self.height - 28,
                color,
                color,
            )


def _draw_geometry(
    canvas: Any,
    geometry: BaseGeometry,
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
    offset_x = x + (width - (max_x - min_x) * scale) / 2
    offset_y = y + (height - (max_y - min_y) * scale) / 2
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
        path = canvas.beginPath()
        coordinates = list(polygon.exterior.coords)
        if not coordinates:
            continue
        first_x, first_y = coordinates[0]
        path.moveTo(offset_x + (first_x - min_x) * scale, offset_y + (first_y - min_y) * scale)
        for point_x, point_y in coordinates[1:]:
            path.lineTo(offset_x + (point_x - min_x) * scale, offset_y + (point_y - min_y) * scale)
        path.close()
        canvas.drawPath(path, fill=1, stroke=1)
