"""
conftest.py — hermetische testopstelling.

Forceert een tijdelijke SQLite-database (los van CI/postgres) zodat tests snel
en geïsoleerd draaien, en stelt een ingelogde admin-client beschikbaar.
"""
import os
import tempfile

import pytest

# DATABASE_URL zetten VOORDAT app.database wordt geïmporteerd
_fd, _DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"
os.environ.setdefault("KIK_ADMIN_EMAIL", "admin@rhadix.nl")
os.environ.setdefault("KIK_ADMIN_PASSWORD", "Rhadixvoordezorg26!")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app                   # noqa: E402


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
def auth(client):
    r = client.post("/api/auth/login",
                    json={"email": "admin@rhadix.nl", "password": "Rhadixvoordezorg26!"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
