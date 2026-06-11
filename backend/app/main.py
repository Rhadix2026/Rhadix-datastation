"""
Rhadix Uitvraag — FastAPI backend
=============================================
Rhadix Datastation — federatief KIK-V datastation (RDF/SPARQL op brondata).
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.bootstrap import init_db
from app.datastation.store import seed_twin
from app.routers import health, meta, admin, org, datastation
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


app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(meta.router, prefix="/api", tags=["meta"])
app.include_router(auth_router, prefix="/api/auth")
app.include_router(admin.router, prefix="/api/admin")
app.include_router(org.router, prefix="/api/org")
app.include_router(datastation.router, prefix="/api")


@app.get("/api")
def root():
    return {"app": "Rhadix Datastation", "edition": "KIK-V", "version": APP_VERSION}
