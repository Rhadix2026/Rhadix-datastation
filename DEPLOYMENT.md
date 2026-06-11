# Rhadix Datastation — Deployment & DTAP

## Overzicht

De Rhadix Datastation gebruikt dezelfde DTAP-strategie als de Rhadix-validation-app, met
drie volledig gescheiden omgevingen. De poorten en volumes zijn anders gekozen,
zodat Rhadix Datastation **naast** de validation-app op dezelfde server kan draaien.

| Omgeving    | Branch    | Frontend | Backend | Database      | Image-tag |
|-------------|-----------|----------|---------|---------------|-----------|
| Development | `develop` | lokaal :5173 | lokaal :8000 | lokaal SQLite/PG | build  |
| Staging     | `staging` | :5181    | :8017   | `datastation_staging`  | `:staging` |
| Productie   | `main`    | :5180    | :8016   | `datastation`  | `:vX.Y.Z`  |

> Staging toont bovenaan een oranje balk (`VITE_KIK_ENV=staging`). Productie niet.

Server-pad: `/opt/datastation-app/`. Container-registry: `ghcr.io/rhadix2026/datastation-backend`
en `…/datastation-frontend`.

---

## Branch-strategie

```
develop  ──(PR)──▶  staging  ──(PR + versie-tag)──▶  main
   │                   │                                │
feature/...      auto-deploy naar staging         handmatige goedkeuring
                  (na groene tests)                vereist + auto-rollback
```

### Werkproces

1. Ontwikkel op `develop` (of een `feature/...`-branch).
2. PR `develop` → `staging`. Na merge: staging wordt automatisch gebouwd, getest en gedeployed.
3. Valideer op `http://<server>:5181`.
4. PR `staging` → `main`.
5. Maak een versie-tag: `git tag v0.4.0 && git push origin main --tags`.
6. GitHub vraagt om goedkeuring (Environment `production`) → keur goed in de Actions-UI.
7. Productie wordt gedeployed; bij een gefaalde health check volgt automatische rollback.

---

## CI/CD-pipelines

| Workflow | Trigger | Doet |
|---|---|---|
| `ci.yml` | push/PR naar develop, staging, main | Pytest + Docker build smoke-test (geen push) |
| `deploy-staging.yml` | push naar `staging` | Test → build `:staging` → push → SSH-deploy → health check |
| `deploy-production.yml` | versie-tag `v*.*.*` of handmatig | Test → build `:vX.Y.Z`+`:latest` → goedkeuring → deploy + rollback |
| `docker-build.yml` | versie-tag | Bouwt en pusht images (zonder deploy) |
| `rollback-staging.yml` | handmatig | Zet staging terug naar een eerdere image-tag |

Tests draaien hermetisch op SQLite (zie `backend/tests/conftest.py`), dus CI heeft
geen externe database nodig.

---

## Vereiste GitHub-secrets

Stel deze in onder **Settings → Secrets and variables → Actions**.

**Staging** (`environment: staging`):

- `STAGING_SSH_HOST`, `STAGING_SSH_USER`, `STAGING_SSH_KEY`
- `STAGING_DB_PASSWORD`
- `STAGING_JWT_SECRET_KEY` — genereer met `python -c "import secrets; print(secrets.token_hex(32))"`
- `STAGING_ADMIN_PASSWORD`

**Productie** (`environment: production`, met verplichte reviewer):

- `PROD_SSH_HOST`, `PROD_SSH_USER`, `PROD_SSH_KEY`
- `PROD_DB_PASSWORD`
- `PROD_JWT_SECRET_KEY` — een **andere** waarde dan staging
- `PROD_ADMIN_PASSWORD`

`GITHUB_TOKEN` is automatisch beschikbaar (voor GHCR-push/pull).

---

## Eenmalige serverinstellingen

```bash
# Op de server
mkdir -p /opt/datastation-app
# .env-bestanden worden door de workflows zelf geschreven uit de secrets.
```

In GitHub: maak de Environments `staging` en `production` aan
(**Settings → Environments**) en zet bij `production` een **required reviewer**,
zodat productie nooit zonder goedkeuring deployt.

---

## Productie koppelen aan de Rhadix-website

De productie-frontend draait op poort `5180`. Koppel die later via de reverse proxy
(nginx/Caddy) van de Rhadix-website aan een (sub)domein, net als bij de
validation-app — bijvoorbeeld `kik.rhadix.nl` → `127.0.0.1:5180`. De frontend
gebruikt relatieve `/api`-URLs, die intern naar de backend worden doorgestuurd.

---

## Lokaal draaien

```bash
docker compose up -d --build      # frontend :5173 · backend :8000
# Tests:
cd backend && pip install -r requirements-dev.txt && pytest tests/ -v
```

## Handmatige rollback

Productie rolt automatisch terug bij een gefaalde health check. Staging kan
handmatig: **Actions → Rollback — Staging → Run workflow** met de gewenste tag.
