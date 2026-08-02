"""Apply Alembic migrations programmatically (app startup path)."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"


def sqlite_url_for(db_path: Path) -> str:
    """Build a SQLAlchemy SQLite URL for an absolute or relative path."""
    resolved = Path(db_path).expanduser().resolve()
    return f"sqlite:///{resolved.as_posix()}"


def upgrade_to_head(db_path: Path) -> None:
    """Run ``alembic upgrade head`` against ``db_path``. Raises on failure."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", sqlite_url_for(db_path))
    command.upgrade(cfg, "head")
