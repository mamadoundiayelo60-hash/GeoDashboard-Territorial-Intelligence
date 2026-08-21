"""Configuration centralisée et validée de l'API."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres injectés par variables d'environnement."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    api_host: str = "0.0.0.0"  # noqa: S104
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_allowed_origins: Annotated[tuple[str, ...], NoDecode] = ("http://localhost:5173",)
    database_url: str = "postgresql+psycopg://geodashboard:change-me@localhost/geodashboard"
    geo_api_base_url: str = "https://geo.api.gouv.fr"
    geo_api_timeout_seconds: float = Field(default=8.0, ge=1.0, le=20.0)
    ign_navigation_base_url: str = "https://data.geopf.fr/navigation"
    ign_navigation_timeout_seconds: float = Field(default=12.0, ge=2.0, le=30.0)
    runtime_data_dir: Path = Path("data/runtime")
    demo_data_path: Path = Path("data/demo/calais-facilities-osm.geojson")
    filosofi_demo_path: Path = Path("data/demo/calais-filosofi-200m.geojson")
    water_mask_path: Path = Path("data/demo/calais-water-mask.geojson")
    eligible_parcels_path: Path = Path("data/demo/calais-eligible-parcels.geojson")
    max_upload_mb: int = Field(default=50, ge=1, le=100)

    @field_validator("database_url")
    @classmethod
    def select_psycopg_driver(cls, value: str) -> str:
        """Normalise les URL PostgreSQL fournies par les hébergeurs."""
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @field_validator("api_allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        """Accepte une liste CSV dans l'environnement."""
        if isinstance(value, str):
            return tuple(origin.strip() for origin in value.split(",") if origin.strip())
        return value

    @field_validator("api_allowed_origins")
    @classmethod
    def reject_wildcard_origin(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Interdit un CORS global, même en configuration accidentelle."""
        if "*" in value:
            raise ValueError("Une origine CORS globale n'est pas autorisée.")
        return value

    @field_validator("geo_api_base_url")
    @classmethod
    def lock_geo_api_host(cls, value: str) -> str:
        """Empêche la configuration d'être détournée vers un hôte arbitraire."""
        if value.rstrip("/") != "https://geo.api.gouv.fr":
            raise ValueError("L'hôte de l'API Geo doit être https://geo.api.gouv.fr.")
        return value.rstrip("/")

    @field_validator("ign_navigation_base_url")
    @classmethod
    def lock_ign_navigation_host(cls, value: str) -> str:
        """Verrouille le connecteur sur le service officiel de la Géoplateforme."""
        if value.rstrip("/") != "https://data.geopf.fr/navigation":
            raise ValueError("L'hôte de navigation IGN doit être https://data.geopf.fr/navigation.")
        return value.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    """Retourne une instance immuable par processus."""
    return Settings()
