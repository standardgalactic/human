"""
app/db.py — SQLAlchemy async session and engine setup
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.models.schema import Base

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://zebratube:zebratube@localhost:5432/zebratube",
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=os.environ.get("SQL_ECHO", "").lower() == "true",
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """Create all tables (development convenience — use Alembic in production)."""
    Base.metadata.create_all(bind=engine)
