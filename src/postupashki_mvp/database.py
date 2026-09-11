"""Database connection and schema initialization."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from postupashki_mvp.config import get_settings


class Base(DeclarativeBase):
    """Base class shared by every database table."""


def create_db_engine() -> Engine:
    settings = get_settings()
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    return create_engine(settings.database_url, connect_args=connect_args)


engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Create all currently declared tables if they do not exist."""
    from postupashki_mvp import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
