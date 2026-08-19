"""Tests de la frontière SQL en lecture seule."""

import pytest

from geodashboard_api.services.sql_guard import SqlGuardError, validate_read_only_sql


def test_accepts_published_view_and_forces_limit() -> None:
    sql = validate_read_only_sql("SELECT name, territory_code FROM geodashboard.v_projects")
    assert "geodashboard.v_projects" in sql
    assert "LIMIT 201" in sql


@pytest.mark.parametrize(
    "query",
    [
        "DELETE FROM geodashboard.v_projects",
        "SELECT * FROM public.users",
        "SELECT pg_sleep(10) FROM geodashboard.v_projects",
        "SELECT * FROM geodashboard.v_projects; DROP TABLE geodashboard.project",
    ],
)
def test_rejects_unsafe_sql(query: str) -> None:
    with pytest.raises(SqlGuardError):
        validate_read_only_sql(query)
