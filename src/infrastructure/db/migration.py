from __future__ import annotations

import os
from pathlib import Path

from alembic.config import Config

from alembic import command
from src.infrastructure.db.sql import DATABASE_URL


def run_migration(database_url: str | None = None) -> None:
    """Run the Alembic migration chain for the repository database."""
    root_dir = Path(__file__).resolve().parents[3]
    alembic_ini = root_dir / "alembic.ini"
    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(root_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url or os.getenv("DATABASE_URL", DATABASE_URL))
    command.upgrade(config, "head")


__all__ = ["run_migration"]
