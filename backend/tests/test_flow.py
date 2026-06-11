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
