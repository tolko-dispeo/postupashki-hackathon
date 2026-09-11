"""Database connection point.

The concrete ORM models will be added only after the logical model is approved.
Keeping engine creation here lets SQLite be replaced with PostgreSQL without
rewriting the API and analytical services.
"""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from postupashki_mvp.config import get_settings


def create_db_engine() -> Engine:
    settings = get_settings()
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    return create_engine(settings.database_url, connect_args=connect_args)
