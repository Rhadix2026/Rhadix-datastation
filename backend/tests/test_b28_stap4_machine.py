"""B-28 stap 4 — Datastation accepteert afnemers met een machinetoken.

Eisen: juiste doelgroep (DATASTATION_AUDIENCE), juiste scope per route, sub
geconfigureerd als afnemer. Tijdens de overgang werkt het serviceaccount-token nog;
met DATASTATION_AFNEMER_ALLEEN_MACHINE=on niet meer. Eigenaarschap van een vraag
hangt aan het afnemerlabel, zodat de overstap geen openstaande vragen verweest.
"""
import logging
import time

import pytest

from app.auth import afnemer as am
from app.routers.datastation import sparql_sjabloon
from tests._testkeys import central_token

SVC = "aaaaaaaa-b28a-4000-8000-0000000000aa"       # huidig serviceaccount (gebruiker)
MACH = "dddddddd-b28d-4000-8000-0000000000dd"      # nieuw machineaccount
ANDER = "eeeeeeee-b28e-4000-8000-0000000000ee"     # machine van een andere afnemer
DOEL = "datastation-staging"
ALLE = "datastation:vragen datastation:resultaat"


def _svc():
    return {"Authorization": "Bearer " + central_token({
        "sub": SVC, "email": "svc@test.rhadix.nl", "role": "ORG_USER", "tenant_name": "Afnemer BV",
        "apps": [], "iat": int(time.time()), "exp": int(time.time()) + 600})}


def _mach(sub=MACH, aud=DOEL, scope=ALLE):
    return {"Authorization": "Bearer " + central_token({
        "sub": sub, "typ": "machine", "aud": aud, "scope": scope, "apps": [], "jti": f"jti-{sub[:4]}",
        "iat": int(time.time()), "exp": int(time.time()) + 600, "name": "machine"})}


@pytest.fixture(autouse=True)
def configuratie(monkeypatch):
    monkeypatch.setenv("DATASTATION_AFNEMERS", f"uitvraag-staging={SVC},uitvraag-staging={MACH},andere={ANDER}")
    monkeypatch.setenv("DATASTATION_AUDIENCE", DOEL)
    monkeypatch.setenv("DATASTATION_DEMO", "on")
    monkeypatch.delenv("DATASTATION_AFNEMER_ALLEEN_MACHINE", raising=False)
    monkeypatch.delenv("DATASTATION_LEGACY_RESULTATEN", raising=False)
    am.reset_limieten()


def _vraag(code="2.1"):
    return {"sparql": sparql_sjabloon(code), "indicator_code": code, "afnemer": "Afnemer BV"}


def test_machine_dient_in_en_haalt_op(client, auth):
    r = client.post("/api/datastation/vragen", headers=_mach(), json=_vraag())
    assert r.status_code == 201 and set(r.json()) == {"query_id", "zaaknummer", "status"}
    qid = r.json()["query_id"]
    client.post(f"/api/datastation/vragen/{qid}/accordeer", headers=auth)
    res = client.get(f"/api/datastation/vragen/{qid}/resultaat", headers=_mach())
    assert res.status_code == 200 and res.json()["status"] == "GEREED"
    door = {(a["actie"], a.get("door")) for a in client.get(f"/api/datastation/vragen/{qid}", headers=auth).json()["audit"]}
    assert ("ONTVANGEN", "afnemer:uitvraag-staging") in door and ("OPGEHAALD", "afnemer:uitvraag-staging") in door


@pytest.mark.parametrize("kwargs", [{"aud": "datastation-productie"}, {"aud": None}])
def test_verkeerde_of_geen_doelgroep(client, kwargs):
    assert client.post("/api/datastation/vragen", headers=_mach(**kwargs), json=_vraag()).status_code == 403


def test_zonder_eigen_doelgroep_fail_closed(client, monkeypatch):
    monkeypatch.delenv("DATASTATION_AUDIENCE")
    assert client.post("/api/datastation/vragen", headers=_mach(), json=_vraag()).status_code == 403


def test_scope_per_route(client, auth):
    alleen_vragen = _mach(scope="datastation:vragen")
    r = client.post("/api/datastation/vragen", headers=alleen_vragen, json=_vraag())
    assert r.status_code == 201
    qid = r.json()["query_id"]
    assert client.get(f"/api/datastation/vragen/{qid}/resultaat", headers=alleen_vragen).status_code == 403
    assert client.post("/api/datastation/vragen", headers=_mach(scope="datastation:resultaat"),
                       json=_vraag()).status_code == 403


def test_machine_zonder_afnemerconfiguratie(client, monkeypatch):
    monkeypatch.setenv("DATASTATION_AFNEMERS", f"uitvraag-staging={SVC}")
    assert client.post("/api/datastation/vragen", headers=_mach(), json=_vraag()).status_code == 403


def test_machine_nooit_op_menselijke_routes(client):
    for pad in ("/api/datastation/vragen?status=open", "/api/datastation/status", "/api/auth/me"):
        assert client.get(pad, headers=_mach()).status_code in (401, 403), pad
    assert client.post("/api/datastation/beantwoord", headers=_mach(), json={"sparql": "x"}).status_code in (401, 403)


def test_overstap_behoudt_openstaande_vragen(client, auth):
    """Vraag ingediend met het serviceaccount, opgehaald met het machinetoken (zelfde
    afnemerlabel); een andere afnemer ziet hem niet."""
    qid = client.post("/api/datastation/vragen", headers=_svc(), json=_vraag()).json()["query_id"]
    client.post(f"/api/datastation/vragen/{qid}/accordeer", headers=auth)
    assert client.get(f"/api/datastation/vragen/{qid}/resultaat", headers=_mach()).json()["status"] == "GEREED"
    assert client.get(f"/api/datastation/vragen/{qid}/resultaat", headers=_mach(sub=ANDER)).status_code == 404


def test_alleen_machine_na_de_overgang(client, monkeypatch):
    assert client.post("/api/datastation/vragen", headers=_svc(), json=_vraag()).status_code == 201
    monkeypatch.setenv("DATASTATION_AFNEMER_ALLEEN_MACHINE", "on")
    assert client.post("/api/datastation/vragen", headers=_svc(), json=_vraag()).status_code == 403
    assert client.post("/api/datastation/vragen", headers=_mach(), json=_vraag()).status_code == 201


def test_log_bevat_jti_maar_geen_token(client, caplog):
    h = _mach()
    with caplog.at_level(logging.INFO):
        client.post("/api/datastation/vragen", headers=h, json=_vraag())
    assert "machine, jti=jti-dddd" in caplog.text
    assert h["Authorization"].split()[1] not in caplog.text
