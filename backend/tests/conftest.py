"""
conftest.py — hermetische testopstelling.

Forceert een tijdelijke SQLite-database (los van CI/postgres) zodat tests snel
en geïsoleerd draaien, en stelt een via SSO geauthenticeerde client beschikbaar.

Authenticatie verloopt uitsluitend via het centrale SureSync ID-token (RS256),
net als in staging en productie. Lokale wachtwoord-login is standaard uit en
wordt door de tests juist als geblokkeerd geverifieerd.
"""
import os
import tempfile

import pytest

# Env zetten VOORDAT app.* wordt geïmporteerd: security.py leest de centrale
# publieke sleutel op moduleniveau.
_fd, _DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"

from tests._testkeys import PUB, central_token  # noqa: E402

os.environ["CENTRAL_JWT_PUBLIC_KEY"] = PUB
os.environ.setdefault("CENTRAL_JWT_ISSUER", "suresync-id")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app                   # noqa: E402

# E-mailadres van de centrale beheerder in de tests. Bewust géén bestaand
# account: bewijst dat JIT-provisioning de gebruiker zelf aanmaakt.
SSO_ADMIN_EMAIL = "sso-admin@test.rhadix.nl"


@pytest.fixture(scope="session")
def client():
    # context manager triggert de startup-event (tabellen + seed)
    with TestClient(app) as c:
        yield c
    try:
        os.unlink(_DB_PATH)
    except OSError:
        pass


@pytest.fixture(scope="session")
def sso_token():
    """Geldig centraal SSO-token voor een platformbeheerder."""
    return central_token({
        "sub": "11111111-1111-1111-1111-111111111111",
        "email": SSO_ADMIN_EMAIL,
        "role": "RHADIX_ADMIN",
        "name": "SSO Beheerder",
        "tenant_name": "Rhadix Platform",
    })


@pytest.fixture(scope="session")
def auth(sso_token):
    """Authorisatie-header op basis van SSO — niet van /api/auth/login."""
    return {"Authorization": f"Bearer {sso_token}"}
