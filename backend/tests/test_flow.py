"""Integratietests voor het Rhadix Datastation."""


def test_health(client):
    assert client.get("/api/health").status_code == 200


def test_login(auth):
    assert "Authorization" in auth


def test_twin_store_geseed(client, auth):
    # bij opstart laadt de twin-store kik:Observatie-data
    d = client.get("/api/datastation/status", headers=auth).json()
    assert d["triples"] > 0 and "twin_observaties" in d["datasets"]


def test_happy_flow_rules(client, auth):
    d = client.get("/api/datastation/rules", headers=auth).json()
    assert d["aantal"] >= 1 and len(d["per_dataset"]) >= 1


def test_beantwoord_publiek(client):
    # beantwoord is server-to-server (geen login) — Uitvraag stuurt de gevalideerde vraag
    sparql = ('PREFIX kik: <https://kik-v.nl/ns#>\n'
              'SELECT (AVG(?w) AS ?waarde) WHERE { ?o a kik:Observatie ; kik:indicator "2.1" ; kik:waarde ?w }')
    r = client.post("/api/datastation/beantwoord", json={"sparql": sparql})
    assert r.status_code == 200
    a = r.json()
    assert a["status"] == "OK" and a["waarde"] > 0


def test_laad_demo_en_beantwoord(client, auth):
    ld = client.post("/api/datastation/laad-testset", headers=auth).json()
    assert ld["status"] == "ok" and ld["records"] == 5
    sparql = ("PREFIX onz-pers: <http://purl.org/ozo/onz-pers#>\n"
              "SELECT (COUNT(?m) AS ?n) WHERE { ?m a onz-pers:Medewerker }")
    ans = client.post("/api/datastation/beantwoord", json={"sparql": sparql}).json()
    assert ans["status"] == "OK" and ans["waarde"] == 5


def test_status_vereist_auth(client):
    assert client.get("/api/datastation/status").status_code == 401


# ── Vraag-inbox (asynchrone beoordeelde beantwoording) ────────────────────────
_INBOX_SPARQL = ('PREFIX kik: <https://kik-v.nl/ns#>\n'
                 'SELECT (AVG(?w) AS ?waarde) WHERE { ?o a kik:Observatie ; '
                 'kik:indicator "2.1" ; kik:waarde ?w }')


def test_inbox_indienen_accorderen_en_ophalen(client, auth):
    # 1. afnemer dient vraag in (publiek)
    r = client.post("/api/datastation/vragen",
                    json={"sparql": _INBOX_SPARQL, "afnemer": "Rhadix Uitvraag",
                          "indicator_code": "2.1"})
    assert r.status_code == 201, r.text
    v = r.json()
    qid = v["query_id"]
    assert v["status"] == "TE_BEOORDELEN" and v["berekende_waarde"] > 0

    # 2. resultaat is nog niet beschikbaar
    res = client.get(f"/api/datastation/vragen/{qid}/resultaat").json()
    assert res["status"] == "IN_BEHANDELING"

    # 3. staat in de inbox
    inbox = client.get("/api/datastation/vragen?status=open", headers=auth).json()
    assert any(x["query_id"] == qid for x in inbox["vragen"])

    # 4. accorderen
    acc = client.post(f"/api/datastation/vragen/{qid}/accordeer", headers=auth).json()
    assert acc["status"] == "VERZONDEN" and acc["handmatig"] is False
    assert acc["definitieve_waarde"] == v["berekende_waarde"]

    # 5. afnemer haalt resultaat op
    res2 = client.get(f"/api/datastation/vragen/{qid}/resultaat").json()
    assert res2["status"] == "GEREED" and res2["waarde"] == v["berekende_waarde"]

    # 6. audittrail bevat de stappen
    det = client.get(f"/api/datastation/vragen/{qid}", headers=auth).json()
    acties = [a["actie"] for a in det["audit"]]
    assert "ONTVANGEN" in acties and "BEREKEND" in acties and "GEACCORDEERD" in acties


def test_inbox_overschrijven(client, auth):
    qid = client.post("/api/datastation/vragen",
                      json={"sparql": _INBOX_SPARQL, "afnemer": "Test"}).json()["query_id"]
    ov = client.post(f"/api/datastation/vragen/{qid}/overschrijf", headers=auth,
                     json={"waarde": 42.5, "toelichting": "handmatig gecorrigeerd"}).json()
    assert ov["status"] == "VERZONDEN" and ov["handmatig"] is True and ov["definitieve_waarde"] == 42.5
    res = client.get(f"/api/datastation/vragen/{qid}/resultaat").json()
    assert res["status"] == "GEREED" and res["waarde"] == 42.5 and res["handmatig"] is True


def test_inbox_stats(client, auth):
    s = client.get("/api/datastation/vragen/stats", headers=auth).json()
    assert s["verzonden"] >= 1
