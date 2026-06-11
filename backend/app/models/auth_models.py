"""
auth_models.py — Tenant (organisatie), User en rollen.
Hiërarchie (zoals Rhadix-validatie):
  PLATFORM_ADMIN  — beheert organisaties, ziet alles
  ORG_ADMIN       — beheert gebruikers binnen één organisatie
  ORG_USER        — reguliere gebruiker
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base, GUID


class UserRole(str, enum.Enum):
    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    ORG_ADMIN      = "ORG_ADMIN"
    ORG_USER       = "ORG_USER"


class Tenant(Base):
    """Een organisatie binnen de Rhadix Uitvraag."""
    __tablename__ = "tenants"

    id         = Column(GUID(), primary_key=True, default=uuid.uuid4)
    slug       = Column(String(63), unique=True, nullable=False, index=True)
    name       = Column(String(255), nullable=False)
    is_active  = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    """Een gebruikersaccount, altijd binnen precies één organisatie."""
    __tablename__ = "users"

    id            = Column(GUID(), primary_key=True, default=uuid.uuid4)
    tenant_id     = Column(GUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    email         = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    full_name     = Column(String(255), nullable=True)
    role          = Column(Enum(UserRole), nullable=False, default=UserRole.ORG_USER)
    is_active     = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant", back_populates="users")
