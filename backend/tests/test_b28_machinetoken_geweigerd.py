"""B-28 stap 3 — een machinetoken (typ=machine) van het centrale platform geeft geen
toegang tot de menselijke routes van deze applicatie en maakt geen gebruiker aan."""
import time
import uuid

import pytest

from app.database import SessionLocal
from app.models.auth_models import User
from tests._testkeys import central_token


def _machine(**extra):
    claims = {"sub": str(uuid.uuid4()), "typ": "machine", "aud": "datastation-staging",
              "scope": "datastation:vragen datastation:resultaat", "apps": [],
              "iat": int(time.time()), "exp": int(time.time()) + 600, "name": "machine-test"}
    claims.update(extra)
    return {"Authorization": "Bearer " + central_token(claims)}


def _aantal_gebruikers():
    db = SessionLocal()
    try:
        return db.query(User).count()
    finally:
        db.close()


@pytest.mark.parametrize("extra", [{}, {"email": "machine@test.rhadix.nl", "apps": ["datastation"]}])
def test_machinetoken_geweigerd_op_auth_me(client, extra):
    voor = _aantal_gebruikers()
    r = client.get("/api/auth/me", headers=_machine(**extra))
    assert r.status_code == 401 and "Machinetoken" in r.text
    assert _aantal_gebruikers() == voor, "er mag geen gebruiker zijn aangemaakt"


def test_gebruikerstoken_werkt_nog(client, auth):
    assert client.get("/api/auth/me", headers=auth).status_code == 200


def test_machinetoken_niet_geconfigureerd_op_afnemerroute(client, monkeypatch):
    """Een machinetoken waarvan de sub geen afnemer is, wordt op de afnemerroute
    expliciet geweigerd (stap 4) en valt nooit terug op het menselijke pad."""
    monkeypatch.delenv("DATASTATION_AFNEMERS", raising=False)
    r = client.post("/api/datastation/vragen", headers=_machine(), json={"sparql": "x", "indicator_code": "2.1"})
    assert r.status_code == 403
