# CLAUDE.md — Rhadix Datastation projectgeheugen

Lees dit bestand aan het begin van elke sessie. Werk de sessie-log bij aan het eind.

## Project
Het federatieve **KIK-V-datastation** in de Rhadix-stack: brondata van een
zorgaanbieder wordt lokaal afgebeeld op KIK-V-concepten (RDF), in een triple store
geladen, en **gevalideerde vragen (SPARQL) worden hier berekend**. Data blijft bij
de bron; alleen het antwoord reist.
- **Repo:** https://github.com/Rhadix2026/Rhadix-datastation
- **Stack:** React/Vite (frontend), FastAPI (Python 3.12), rdflib/Apache Jena Fuseki, Docker
- **Zusterprojecten:** Rhadix-datavalidatie (rekenhart-oorsprong) en rhadix-uitvraag (afnemerskant)
- **Rekenhart:** uit de reconciliatie-module van Datavalidatie — `rdf_store`,
  `calculation_engine`, `rule_engine` + `rules/*.yaml`.

## Huisstijl
Rhadix-huisstijl (navy `--blue/#1A2847`, accent `#6FA8D0`, Oxanium-font), gelijk aan
Datavalidatie/Uitvraag.

## Branch-strategie & deployen
| Branch | Omgeving | Poorten (fe/be) | Deploy |
|--------|----------|-----------------|--------|
| `staging` | Staging | 5181 / 8017 | push = automatisch |
| `v*.*.*` tag op `main` | Productie (`datastation.rhadix.nl`) | 5180 / 8016 | GitHub Actions + handmatige goedkeuring |

- Werk in `/tmp`-clone (niet de gemounte map). Na merge naar main ook staging uitlijnen.
- Deploy-workflow schrijft zelf `.env.production` op de server uit secrets
  (`PROD_DB_PASSWORD`, `PROD_JWT_SECRET_KEY`, `PROD_ADMIN_PASSWORD`, `PROD_SSH_*`).
- `VALIDATION_API_URL=https://app.rhadix.nl` (koppeling met Datavalidatie).
- **Huidige versie:** v1.0.0 (eerste productie-release).

## Server / infra
- Server `46.224.224.26`; reverse proxy = **nginx** (Cloudflare alleen DNS).
- nginx-vhost `datastation.rhadix.nl` → `/api/` naar `127.0.0.1:8016`, `/` naar `:5180`,
  gedeeld wildcard Origin-cert `/etc/ssl/rhadix/rhadix.*`.

## Endpoints (backend)
`status`, `rules`, `laad-testset`, `upload`, `beantwoord`, `/api/health`.

## Sessie-log
| Datum | Versie | Wijziging |
|-------|--------|-----------|
| 2026-06-17 | v1.0.0 | Eerste productie-release. nginx-vhost + Cloudflare DNS `datastation.rhadix.nl` (5180/8016). Geactiveerd in de Datavalidatie-portal. CLAUDE.md rechtgezet (was per abuis een kopie van de Uitvraag-versie). |
| 2026-06-12 | — | Datastation-inbox: 'Alles accorderen' (bulk) + upload-paneel in dashboard. |
| 2026-06-11 | — | Mijlpaal 1: rekenhart + API (brondata → concepten → RDF → SPARQL → antwoord). |
