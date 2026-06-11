"""Integratietests voor het Rhadix Datastation."""


def test_health(client):
    assert client.get("/api/health").status_code == 200


def test_login(auth):
    assert "Authorization" in auth


def test_status_leeg(client, auth):
    d = client.get("/api/datastation/status", headers=auth).json()
    assert d["datasets"] == {} and d["triples"] == 0


def test_happy_flow_rules(client, auth):
    d = client.get("/api/datastation/rules", headers=auth).json()
    assert d["aantal"] >= 1 and len(d["per_dataset"]) >= 1


def test_laad_en_beantwoord(client, auth):
    ld = client.post("/api/datastation/laad-testset", headers=auth).json()
    assert ld["status"] == "ok" and ld["records"] >= 1 and ld["triples"] >= 1

    st = client.get("/api/datastation/status", headers=auth).json()
    assert st["triples"] >= 1 and len(st["datasets"]) >= 1

    sparql = ("PREFIX onz-pers: <http://purl.org/ozo/onz-pers#>\n"
              "SELECT (COUNT(?m) AS ?n) WHERE { ?m a onz-pers:Medewerker }")
    ans = client.post("/api/datastation/beantwoord", headers=auth, json={"sparql": sparql}).json()
    assert ans["status"] == "OK" and ans["waarde"] == 5

    # reset leegt de store
    client.post("/api/datastation/reset", headers=auth)
    assert client.get("/api/datastation/status", headers=auth).json()["triples"] == 0


def test_auth_handhaving(client):
    assert client.get("/api/datastation/status").status_code == 401
