"""B-28 — afnemers authenticeren met een centraal serviceaccount.

Een afnemer is een centraal account (Rhadix Datavalidatie) waarvan de `sub` in
DATASTATION_AFNEMERS staat. Hij mag alleen een gevalideerde vraag indienen en het
resultaat van de eigen vraag ophalen; verder niets.
"""
import logging
import time

import pytest
from jose import jwt

from app.auth import afnemer as am
from app.routers.datastation import sparql_sjabloon
from tests._testkeys import PRIV, central_token

SUB_A = "aaaaaaaa-b28a-4000-8000-000000000001"
SUB_B = "bbbbbbbb-b28b-4000-8000-000000000002"


def _tok(sub, **extra):
    claims = {"sub": sub, "email": f"svc-{sub[:4]}@test.rhadix.nl", "role": "ORG_USER",
              "tenant_name": "Afnemer BV", "apps": [], "exp": int(time.time()) + 600}
    claims.update(extra)
    return central_token(claims)


def _H(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(autouse=True)
def configuratie(monkeypatch):
    monkeypatch.setenv("DATASTATION_AFNEMERS", f"afnemer-a={SUB_A}, afnemer-b={SUB_B}")
    monkeypatch.setenv("DATASTATION_DEMO", "on")
    monkeypatch.delenv("DATASTATION_LEGACY_RESULTATEN", raising=False)
    monkeypatch.delenv("DATASTATION_M2M_ENFORCE", raising=False)
    am.reset_limieten()
    yield
    am.reset_limieten()


def _vraag(code="2.1", **extra):
    body = {"sparql": sparql_sjabloon(code), "indicator_code": code, "afnemer": "Afnemer BV",
            "zorgaanbieder": "Twin"}
    body.update(extra)
    return body


def _indienen(client, sub=SUB_A, **extra):
    return client.post("/api/datastation/vragen", headers=_H(_tok(sub)), json=_vraag(**extra))


# ── Authenticatie ────────────────────────────────────────────────────────────
@pytest.mark.parametrize("route,methode", [
    ("/api/datastation/vragen", "post"), ("/api/datastation/beantwoord", "post"),
    ("/api/datastation/vragen/00000000-0000-4000-8000-000000000000/resultaat", "get"),
])
def test_zonder_token_401(client, route, methode):
    r = getattr(client, methode)(route, json=_vraag()) if methode == "post" else client.get(route)
    assert r.status_code == 401


def test_vervalst_en_verlopen_token(client):
    nep = jwt.encode({"sub": SUB_A, "iss": "suresync-id", "email": "x@y", "exp": int(time.time()) + 600},
                     "geen-sleutel", algorithm="HS256")
    assert client.post("/api/datastation/vragen", headers=_H(nep), json=_vraag()).status_code == 401
    verlopen = _tok(SUB_A, exp=int(time.time()) - 10)
    assert client.post("/api/datastation/vragen", headers=_H(verlopen), json=_vraag()).status_code == 401
    ander_iss = jwt.encode({"sub": SUB_A, "iss": "iemand-anders", "email": "x@y",
                            "exp": int(time.time()) + 600}, PRIV, algorithm="RS256")
    assert client.post("/api/datastation/vragen", headers=_H(ander_iss), json=_vraag()).status_code == 401


def test_centraal_account_dat_geen_afnemer_is(client, monkeypatch):
    """Een gewone centrale gebruiker zonder datastation-applicatie komt er niet in."""
    monkeypatch.setenv("APP_ACCESS_ENFORCE", "on")
    t = _tok("cccccccc-0000-4000-8000-000000000003", apps=["uitvraag"])
    assert client.post("/api/datastation/vragen", headers=_H(t), json=_vraag()).status_code == 403


# ── Afnemer: indienen ────────────────────────────────────────────────────────
def test_afnemer_dient_in_en_krijgt_alleen_zaaknummer(client):
    r = _indienen(client)
    assert r.status_code == 201, r.text
    assert set(r.json()) == {"query_id", "zaaknummer", "status"}, "geen berekende waarde naar de afnemer"


@pytest.mark.parametrize("wijziging", [
    {"sparql": "SELECT * WHERE { ?s ?p ?o }"},
    {"sparql": sparql_sjabloon("2.1") + " # extra"},
    {"sparql": sparql_sjabloon("1.1")},                       # sjabloon van een andere indicator
    {"indicator_code": None},
    {"indicator_code": 'x" } ; ?s ?p ?o . { "'},
])
def test_afnemer_alleen_gevalideerd_sjabloon(client, wijziging):
    body = _vraag(); body.update(wijziging)
    r = client.post("/api/datastation/vragen", headers=_H(_tok(SUB_A)), json=body)
    assert r.status_code == 422, r.text


def test_omvanglimiet(client, auth):
    r = client.post("/api/datastation/vragen", headers=auth, json={"sparql": "x" * 9000})
    assert r.status_code == 422


def test_afnemer_kan_geen_vrije_query_via_beantwoord(client):
    r = client.post("/api/datastation/beantwoord", headers=_H(_tok(SUB_A)), json={"sparql": "SELECT 1 {}"})
    assert r.status_code == 403


@pytest.mark.parametrize("route,methode", [
    ("/api/datastation/vragen?status=open", "get"), ("/api/datastation/status", "get"),
    ("/api/datastation/vragen/stats", "get"), ("/api/datastation/vragen/accordeer-alles", "post"),
    ("/api/datastation/reset", "post"),
])
def test_afnemer_geweigerd_op_gebruikersroutes(client, monkeypatch, route, methode):
    """Ook als de applicatiecontrole op 'warn' staat of iemand de afnemer later
    een applicatie toewijst."""
    monkeypatch.setenv("APP_ACCESS_ENFORCE", "warn")
    t = _tok(SUB_A, apps=["datastation"])
    r = getattr(client, methode)(route, headers=_H(t))
    assert r.status_code == 403, (route, r.status_code)


# ── Resultaat alleen voor de eigen afnemer ───────────────────────────────────
def test_resultaat_alleen_voor_eigen_afnemer(client, auth):
    qid = _indienen(client).json()["query_id"]
    pad = f"/api/datastation/vragen/{qid}/resultaat"
    assert client.get(pad, headers=_H(_tok(SUB_A))).json()["status"] == "IN_BEHANDELING"
    assert client.get(pad, headers=_H(_tok(SUB_B))).status_code == 404
    client.post(f"/api/datastation/vragen/{qid}/accordeer", headers=auth)
    r = client.get(pad, headers=_H(_tok(SUB_A))).json()
    assert r["status"] == "GEREED" and r["waarde"] is not None
    assert client.get(pad, headers=_H(_tok(SUB_B))).status_code == 404
    det = client.get(f"/api/datastation/vragen/{qid}", headers=auth).json()
    door = {(a["actie"], a.get("door")) for a in det["audit"]}
    assert ("ONTVANGEN", "afnemer:afnemer-a") in door and ("OPGEHAALD", "afnemer:afnemer-a") in door


def test_ingetrokken_afnemer_direct_geweigerd(client, monkeypatch):
    qid = _indienen(client).json()["query_id"]
    monkeypatch.setenv("DATASTATION_AFNEMERS", f"afnemer-b={SUB_B}")
    r = client.get(f"/api/datastation/vragen/{qid}/resultaat", headers=_H(_tok(SUB_A)))
    assert r.status_code in (401, 403)
    assert _indienen(client).status_code in (401, 403)


def test_legacy_vragen_alleen_met_vlag(client, auth, monkeypatch):
    """Vragen van vóór B-28 hebben geen eigenaar (bestaande twin-koppeling op staging)."""
    monkeypatch.setenv("DATASTATION_M2M_ENFORCE", "off")
    qid = client.post("/api/datastation/vragen", json=_vraag()).json()["query_id"]   # oud, anoniem
    monkeypatch.setenv("DATASTATION_M2M_ENFORCE", "on")
    pad = f"/api/datastation/vragen/{qid}/resultaat"
    assert client.get(pad, headers=_H(_tok(SUB_A))).status_code == 404
    monkeypatch.setenv("DATASTATION_LEGACY_RESULTATEN", "on")
    assert client.get(pad, headers=_H(_tok(SUB_A))).status_code == 200


def test_gebruiker_met_toegang_blijft_werken(client, auth):
    """De eigen UI van het datastation (testvraag, resultaat) blijft werken."""
    r = client.post("/api/datastation/vragen", headers=auth,
                    json={"sparql": "PREFIX kik: <https://kik-v.nl/ns#>\nSELECT (AVG(?w) AS ?waarde) "
                                    "WHERE { ?o a kik:Observatie ; kik:indicator \"2.1\" ; kik:waarde ?w }",
                          "afnemer": "Rhadix Uitvraag (test)", "indicator_code": "2.1"})
    assert r.status_code == 201 and "berekende_waarde" in r.json()


# ── Begrenzing, demo-stand, noodrem, logging ─────────────────────────────────
def test_uurlimiet_per_afnemer(client, monkeypatch):
    monkeypatch.setenv("DATASTATION_AFNEMER_VRAGEN_PER_UUR", "3")
    assert [_indienen(client).status_code for _ in range(3)] == [201, 201, 201]
    r = _indienen(client)
    assert r.status_code == 429 and int(r.headers["Retry-After"]) > 0
    assert _indienen(client, sub=SUB_B).status_code == 201, "de limiet geldt per afnemer"


def test_geen_demodata_buiten_demo_stand(client, monkeypatch):
    import app.routers.datastation as ds
    gezien = []
    monkeypatch.setattr(ds, "zorg_voor_observatie", lambda code: gezien.append(code))
    monkeypatch.setenv("DATASTATION_DEMO", "off")
    _indienen(client, code="9.99")
    assert gezien == []
    monkeypatch.setenv("DATASTATION_DEMO", "on")
    _indienen(client, code="9.98")
    assert gezien == ["9.98"]


def test_noodrem_off_herstelt_oud_gedrag(client, monkeypatch):
    monkeypatch.setenv("DATASTATION_M2M_ENFORCE", "off")
    assert client.post("/api/datastation/vragen", json=_vraag()).status_code == 201


def test_geen_geheimen_in_de_log(client, caplog):
    t = _tok(SUB_A)
    with caplog.at_level(logging.INFO):
        _indienen(client)
        client.post("/api/datastation/vragen", headers=_H(t + "x"), json=_vraag())
        client.get("/api/datastation/vragen?status=open", headers=_H(t))
    tekst = caplog.text
    assert "afnemer afnemer-a" in tekst and "geweigerd" in tekst
    assert t not in tekst and t[:40] not in tekst and "Bearer" not in tekst


def test_configuratie_ongeldige_regels_genegeerd(monkeypatch):
    monkeypatch.setenv("DATASTATION_AFNEMERS", "Hoofd Letters=x, =y, ok-label=z, geen-sub=")
    assert am.afnemers() == {"z": "ok-label"}
