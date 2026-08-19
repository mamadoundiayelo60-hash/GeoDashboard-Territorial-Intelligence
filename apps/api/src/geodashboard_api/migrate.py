"""Exécuteur minimal des migrations SQL idempotentes au démarrage."""

import os
from pathlib import Path

from sqlalchemy import create_engine

from geodashboard_api.config import get_settings


def main() -> None:
    """Applique les fichiers SQL triés dans une transaction par fichier."""
    migration_dir = Path(os.getenv("MIGRATIONS_DIR", "database/migrations"))
    if not migration_dir.is_dir():
        raise RuntimeError(f"Répertoire de migrations absent : {migration_dir}")
    engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    try:
        for path in sorted(migration_dir.glob("*.sql")):
            with engine.begin() as connection:
                connection.exec_driver_sql(path.read_text(encoding="utf-8"))
            print(f"Migration appliquée : {path.name}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
