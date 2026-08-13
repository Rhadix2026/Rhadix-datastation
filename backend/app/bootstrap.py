"""bootstrap.py — tabellen aanmaken en een platform-admin seeden."""
from __future__ import annotations

import os
import uuid

from app.database import Base, SessionLocal, engine
from app.models.auth_models import Tenant, User, UserRole
from app.models import datastation_models  # noqa: F401  (tabellen registreren)
from app.auth.security import hash_password


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_columns()
    _ensure_platform_tenant()
    _seed_platform_admin()


def _ensure_columns() -> None:
    """Lichtgewicht migratie: voeg ontbrekende kolommen toe aan bestaande tabellen."""
    from sqlalchemy import inspect, text
    wanted = {"datastation_vragen": [("zorgaanbieder", "VARCHAR(255)"),
                                     ("indicator_label", "VARCHAR(255)")]}
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, cols in wanted.items():
            if not insp.has_table(table):
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in cols:
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))



def _ensure_platform_tenant() -> uuid.UUID:
    """Borg de platform-tenant. Functioneel nodig als thuisbasis van de beheerder.

    Losgekoppeld van het aanmaken van gebruikersaccounts: de tenant-bootstrap moet
    altijd draaien, het seeden van een account is een aparte keuze.
    """
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.slug == "platform").first()
        if not tenant:
            tenant = Tenant(id=uuid.uuid4(), slug="platform", name="Rhadix Platform", is_active=True)
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
        return tenant.id
    finally:
        db.close()


def _seed_platform_admin() -> None:
    """Borg de vaste platform-admin — NIET-DESTRUCTIEF.

    Raakt andere gebruikers niet aan. Eerder werd hier bij elke start
    `TRUNCATE TABLE users RESTART IDENTITY CASCADE` uitgevoerd, waardoor de hele
    gebruikerstabel bij iedere deploy of herstart werd gewist — inclusief de
    gebruikers die via SSO just-in-time waren aangemaakt. Dat gedrag is verwijderd;
    JIT-gebruikers blijven nu bestaan over herstarts heen.

    Met AUTH_RESET=0 wordt het seeden overgeslagen.
    """
    email = "admin@rhadix.nl"
    password = "Rhadixvoordezorg26!"
    if os.getenv("AUTH_RESET", "1").lower() in ("0", "false", "no"):
        return

    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.slug == "platform").first()
        if not tenant:
            tenant = Tenant(id=uuid.uuid4(), slug="platform", name="Rhadix Platform", is_active=True)
            db.add(tenant)
            db.flush()

        admin = db.query(User).filter(User.email == email).first()
        if admin:
            admin.password_hash = hash_password(password)
            admin.is_active = True
            admin.role = UserRole.PLATFORM_ADMIN
            admin.tenant_id = tenant.id
        else:
            db.add(User(
                id=uuid.uuid4(), tenant_id=tenant.id, email=email,
                full_name="Platformbeheerder", password_hash=hash_password(password),
                role=UserRole.PLATFORM_ADMIN, is_active=True,
            ))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()



