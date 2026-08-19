"""Exécution courte d'une requête SQL déjà validée."""

from time import perf_counter
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from geodashboard_api.models import SqlQueryResult


class SqlExecutionError(RuntimeError):
    """Indisponibilité ou rejet de la base, sans détails sensibles."""


def execute_read_only(
    database_url: str, validated_sql: str, row_limit: int = 200
) -> SqlQueryResult:
    """Exécute dans une transaction read-only avec timeout serveur."""
    started = perf_counter()
    engine = create_engine(database_url, pool_pre_ping=True, pool_timeout=3)
    try:
        with engine.connect() as connection, connection.begin():
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            connection.exec_driver_sql("SET LOCAL statement_timeout = '3000ms'")
            result = connection.execute(text(validated_sql))
            columns = list(result.keys())
            raw_rows = [list(row) for row in result.fetchmany(row_limit + 1)]
        truncated = len(raw_rows) > row_limit
        rows: list[list[Any]] = raw_rows[:row_limit]
        return SqlQueryResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            truncated=truncated,
            duration_ms=round((perf_counter() - started) * 1000),
        )
    except SQLAlchemyError as exc:
        raise SqlExecutionError(
            "La source PostGIS n'est pas disponible ou a refusé la requête."
        ) from exc
    finally:
        engine.dispose()
