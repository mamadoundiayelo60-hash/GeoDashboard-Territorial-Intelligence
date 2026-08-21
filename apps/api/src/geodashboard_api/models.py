"""Contrats publics de l'API GeoDashboard."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CommuneSummary(BaseModel):
    """Commune désambiguïsée dans les résultats de recherche."""

    code: str = Field(pattern=r"^[0-9A-Z]{5}$")
    name: str
    department_code: str | None = None
    region_code: str | None = None
    postal_codes: list[str] = Field(default_factory=list)
    population: int | None = Field(default=None, ge=0)


class TerritoryProfile(CommuneSummary):
    """Profil communal accompagné de sa géométrie web."""

    geometry: dict[str, Any]
    bbox: tuple[float, float, float, float]
    area_km2: float = Field(gt=0)
    density_per_km2: float | None = Field(default=None, ge=0)
    source: str = "API Découpage administratif — data.gouv.fr"


class QualityReport(BaseModel):
    """Diagnostic synthétique d'une couche importée."""

    score: int = Field(ge=0, le=100)
    invalid_geometries: int = Field(ge=0)
    empty_geometries: int = Field(ge=0)
    duplicate_geometries: int = Field(ge=0)
    null_cells: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)


class LayerSummary(BaseModel):
    """Couche normalisée et isolée dans une session."""

    id: str
    name: str
    source_format: str
    feature_count: int = Field(ge=0)
    field_count: int = Field(ge=0)
    geometry_types: list[str]
    crs: str
    quality: QualityReport
    preview: dict[str, Any] | None = None


class ScenarioLocation(BaseModel):
    """Équipement hypothétique exprimé en coordonnées WGS84."""

    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)


class DecisionWeights(BaseModel):
    """Pondérations explicites d'un classement de sites."""

    population: float = Field(default=0.45, ge=0, le=1)
    vulnerability: float = Field(default=0.35, ge=0, le=1)
    equity: float = Field(default=0.20, ge=0, le=1)


class DecisionRequest(BaseModel):
    """Paramètres d'une étude d'implantation territoriale."""

    territory_geometry: dict[str, Any]
    territory_name: str = Field(min_length=1, max_length=120)
    territory_code: str = Field(pattern=r"^[0-9A-Z]{5}$")
    population: int = Field(ge=1)
    mode: str = Field(default="pedestrian", pattern=r"^(pedestrian|bicycle|car)$")
    threshold_minutes: int = Field(default=15, ge=5, le=30)
    weights: DecisionWeights = Field(default_factory=DecisionWeights)


class DecisionResult(BaseModel):
    """Diagnostic d'accessibilité et classement multicritère cartographiable."""

    method: str
    data_status: str
    current_access_rate: float
    scenario_access_rate: float
    gained_people: int
    underserved_people: int
    equity_gain: float
    facilities: dict[str, Any]
    demand_grid: dict[str, Any]
    candidates: dict[str, Any]
    current_service_area: dict[str, Any]
    scenario_service_area: dict[str, Any]
    recommendation: dict[str, Any]
    sources: list[dict[str, str]]
    limitations: list[str]


class CoverageRequest(BaseModel):
    """Paramètres bornés d'un diagnostic de couverture géométrique."""

    layer_id: str
    territory_geometry: dict[str, Any]
    distance_m: float = Field(default=500, ge=50, le=10_000)
    population: int | None = Field(default=None, ge=0)
    scenario_locations: list[ScenarioLocation] = Field(default_factory=list, max_length=20)


class CoverageIndicators(BaseModel):
    """Indicateurs comparables d'une situation territoriale."""

    equipment_count: int = Field(ge=0)
    covered_area_km2: float = Field(ge=0)
    uncovered_area_km2: float = Field(ge=0)
    coverage_rate: float = Field(ge=0, le=100)
    estimated_covered_population: int | None = Field(default=None, ge=0)


class CoverageResult(BaseModel):
    """Diagnostic actuel et scénario, accompagné des géométries web."""

    method: str
    distance_m: float
    current: CoverageIndicators
    scenario: CoverageIndicators
    gain_points: float
    covered_geometry: dict[str, Any]
    uncovered_geometry: dict[str, Any]
    scenario_covered_geometry: dict[str, Any]
    scenario_uncovered_geometry: dict[str, Any]
    interpretation: str
    warnings: list[str]


class CalculatedFieldRequest(BaseModel):
    """Expression contrôlée appliquée à une couche de la session."""

    layer_id: str
    field_name: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
    expression: str = Field(min_length=1, max_length=500)


class CalculatedFieldResult(BaseModel):
    """Résultat et aperçu d'un champ calculé."""

    layer: LayerSummary
    field_name: str
    preview: list[Any]


class SqlQueryRequest(BaseModel):
    """Requête experte bornée."""

    query: str = Field(min_length=1, max_length=10_000)


class SqlQueryResult(BaseModel):
    """Résultat tabulaire limité et traçable."""

    columns: list[str]
    rows: list[list[Any]]
    row_count: int = Field(ge=0, le=200)
    truncated: bool
    duration_ms: int = Field(ge=0)


class HistoryEvent(BaseModel):
    """Événement reproductible d'une session d'étude."""

    id: str
    event_type: str
    summary: str
    parameters: dict[str, Any]
    created_at: str


class ReportTemplate(StrEnum):
    """Formats de restitution maîtrisés."""

    A4_PORTRAIT = "a4_portrait"
    A4_LANDSCAPE = "a4_landscape"
    A3_LANDSCAPE = "a3_landscape"


class ReportTerritory(BaseModel):
    """Informations territoriales imprimées dans le rapport."""

    name: str = Field(min_length=1, max_length=120)
    code: str = Field(pattern=r"^[0-9A-Z]{5}$")
    area_km2: float = Field(gt=0)
    population: int | None = Field(default=None, ge=0)


class ReportRequest(BaseModel):
    """Contenu borné d'un rapport décisionnel."""

    title: str = Field(
        default="Diagnostic de couverture territoriale", min_length=1, max_length=140
    )
    template: ReportTemplate = ReportTemplate.A4_PORTRAIT
    territory: ReportTerritory
    diagnostic: CoverageResult
    source_layer_name: str = Field(min_length=1, max_length=120)
    author: str = Field(default="Mamadou Ndiaye LO", min_length=1, max_length=120)
    include_details: bool = True
    include_methodology: bool = True
    include_sources: bool = True


class DecisionReportRequest(BaseModel):
    """Scénario TerriScope sérialisé dans une note décisionnelle PDF."""

    title: str = Field(default="Étude d'implantation d'un service de santé", max_length=140)
    territory: ReportTerritory
    territory_geometry: dict[str, Any]
    decision: DecisionResult
    mode: str = Field(pattern=r"^(pedestrian|bicycle|car)$")
    threshold_minutes: int = Field(ge=5, le=30)
    weights: DecisionWeights
    author: str = Field(default="Mamadou Ndiaye LO", min_length=1, max_length=120)
