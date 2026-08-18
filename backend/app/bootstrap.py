"""bootstrap.py — tabellen aanmaken en de platform-tenant borgen.

Gebruikers worden NIET meer geseed. Authenticatie verloopt via SSO: Rhadix
Datavalidatie geeft het centrale token uit en deze app provisioneert gebruikers
just-in-time (zie auth/dependencies.py). Een lokaal adminaccount met een in de
code gebakken wachtwoord heeft daardoor geen functie meer.

Bestaande accounts blijven staan: deze module maakt, wijzigt en verwijdert geen
gebruikers.
"""
from __future__ import annotations

import uuid

from app.database import Base, SessionLocal, engine
from app.models.auth_models import Tenant
from app.models import datastation_models  # noqa: F401  (tabellen registreren)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_columns()
    _ensure_platform_tenant()


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
    """Borg de platform-tenant.

    Functioneel nodig als thuisbasis binnen dit datastation. Volledig losgekoppeld
    van gebruikersaccounts: deze functie raakt de users-tabel niet aan. Gebruikers
    ontstaan uitsluitend via SSO/JIT-provisioning.
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
