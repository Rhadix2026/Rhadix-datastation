"""
Rhadix Uitvraag — FastAPI backend
=============================================
Rhadix Datastation — federatief KIK-V datastation (RDF/SPARQL op brondata).
"""
from __future__ import annotations

import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.bootstrap import init_db
from app.datastation.store import seed_twin
from app.routers import health, meta, admin, org, datastation
from app.auth.app_access import require_app_access
from app.auth.router import router as auth_router

APP_VERSION = "0.6.0"

app = FastAPI(title="Rhadix Datastation API", version=APP_VERSION)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    init_db()
    seed_twin()


# Applicatietoegang op basis van de centrale apps-claim (zie auth/app_access.py).
# Zonder token doet de dependency niets, zodat publieke routes (health, meta) en de
# server-to-server routes van het datastation ongewijzigd blijven werken.
#
# /api/auth blijft bewust ONgegate: zo kan de frontend ook zonder toewijzing nog
# /auth/me ophalen en de gebruiker een verklarende melding tonen in plaats van een
# blinde 401/403-lus.
_app_access = [Depends(require_app_access)]

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(meta.router, prefix="/api", tags=["meta"])
app.include_router(auth_router, prefix="/api/auth")
app.include_router(admin.router, prefix="/api/admin", dependencies=_app_access)
app.include_router(org.router, prefix="/api/org", dependencies=_app_access)
app.include_router(datastation.router, prefix="/api", dependencies=_app_access)


@app.get("/api")
def root():
    return {"app": "Rhadix Datastation", "edition": "KIK-V", "version": APP_VERSION}
