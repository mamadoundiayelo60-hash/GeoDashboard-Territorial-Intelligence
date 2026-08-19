"""Tests des garde-fous de configuration."""

import pytest
from pydantic import ValidationError

from geodashboard_api.config import Settings


def test_cors_wildcard_is_rejected() -> None:
    """Une mauvaise variable ne doit pas ouvrir l'API à tous les sites."""
    with pytest.raises(ValidationError):
        Settings(api_allowed_origins=("*",))


def test_csv_origins_are_parsed() -> None:
    """Plusieurs frontends autorisés sont interprétés sans espaces parasites."""
    settings = Settings(api_allowed_origins="https://app.test, https://admin.test")
    assert settings.api_allowed_origins == ("https://app.test", "https://admin.test")


def test_geo_api_host_cannot_be_redirected() -> None:
    """La configuration ne doit pas ouvrir une primitive SSRF."""
    with pytest.raises(ValidationError):
        Settings(geo_api_base_url="https://example.invalid")


@pytest.mark.parametrize("prefix", ["postgres://", "postgresql://"])
def test_hosted_database_urls_select_psycopg(prefix: str) -> None:
    settings = Settings(database_url=f"{prefix}user:pass@db.example/geodashboard")
    assert settings.database_url.startswith("postgresql+psycopg://")
