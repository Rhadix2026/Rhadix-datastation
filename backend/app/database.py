"""
database.py — SQLAlchemy engine, sessie en portable GUID-type.
Werkt op PostgreSQL (productie) én SQLite (tests) dankzij de GUID TypeDecorator.
"""
from __future__ import annotations

import os
import uuid

from sqlalchemy import create_engine, types
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kik_starter.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class GUID(types.TypeDecorator):
    """Platform-onafhankelijk UUID-type: PG UUID op Postgres, CHAR(36) elders."""
    impl = types.CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(types.CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
