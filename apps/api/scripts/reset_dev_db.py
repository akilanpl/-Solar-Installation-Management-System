"""Drop and recreate the local development schema.

Refuses any database other than `solarops` and any environment other than
development. It does not know how to target production, and it will not run
against `solarops_test` (pytest owns that database).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import command
from alembic.config import Config
from app.core.config import Settings
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url


def main() -> None:
    if "--yes" not in sys.argv:
        raise SystemExit("Refusing to reset the database without --yes.")
    settings = Settings()
    database = make_url(settings.database_url).database or ""
    if settings.app_env != "development" or database != "solarops" or "prod" in database:
        raise SystemExit(f"Refusing to reset app_env={settings.app_env} database={database}.")
    engine = create_engine(settings.database_url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        connection.execute(text("GRANT ALL ON SCHEMA public TO solarops"))
        connection.execute(text("GRANT ALL ON SCHEMA public TO public"))
    engine.dispose()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    print("Development database reset and migrated.")


if __name__ == "__main__":
    main()
