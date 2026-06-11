# Rhadix Datastation

Het federatieve **KIK-V-datastation** in de Rhadix-stack: brondata van een
zorgaanbieder wordt lokaal afgebeeld op KIK-V-concepten (RDF), in een triple
store (Fuseki, met rdflib-fallback) geladen, en **gevalideerde vragen (SPARQL)
worden hier berekend**. De data blijft bij de bron; alleen het antwoord reist.

> Status: **mijlpaal 1 — rekenhart + API**. Brondata → concepten → RDF → SPARQL →
> antwoord werkt end-to-end. Endpoints: `status`, `rules`, `laad-testset`,
> `upload`, `beantwoord`. Volgende stap: koppelen aan Rhadix Uitvraag (de
> `datastation_url`-haak) zodat de KIK-V-keten end-to-end draait.

## Stack
React 18 + Vite · FastAPI (Python 3.12) · rdflib/Apache Jena Fuseki · Docker · DTAP.

## Onder de motorkap
Het rekenhart komt uit de reconciliatie-module van Rhadix-datavalidatie:
`rdf_store` (RDF bouwen + SPARQL op Fuseki/rdflib), `calculation_engine`
(brondata laden + regels), `rule_engine` + `rules/*.yaml` (happy-flow indicatoren).

## Lokaal draaien
```bash
docker compose up -d --build      # frontend :5173 · backend :8000
cd backend && pip install -r requirements-dev.txt && pytest tests/ -v
```

## API (kern)
```
POST /api/datastation/laad-testset      demo-brondata → concepten → RDF
POST /api/datastation/upload            echte CSV + kolom→concept-mapping
POST /api/datastation/beantwoord        { sparql } → { status, waarde, backend }
GET  /api/datastation/status            triple store, datasets, triples
GET  /api/datastation/rules             happy-flow indicatoren
```

Zie [DEPLOYMENT.md](DEPLOYMENT.md) voor de DTAP-flow.
