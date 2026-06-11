"""datastation.py — API van het Rhadix Datastation."""
from __future__ import annotations

import io
import json
import pathlib

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.models.auth_models import User
from app.datastation import rdf_store
from app.datastation.store import STATION
from app.datastation.rule_engine import RuleEngine

router = APIRouter(tags=["datastation"])

_DEMO_DIR = pathlib.Path(__file__).parent.parent / "datastation" / "demo"
_RULES_DIR = pathlib.Path(__file__).parent.parent / "datastation" / "rules"

_rules = RuleEngine()
if _RULES_DIR.exists():
    _rules.load_directory(_RULES_DIR)


class SparqlVraag(BaseModel):
    sparql: str


@router.get("/datastation/status")
def status(current: User = Depends(get_current_user)):
    return {
        "fuseki": bool(rdf_store.FUSEKI_URL),
        "datasets": STATION.datasets,
        "triples": STATION.triple_count,
    }


@router.get("/datastation/rules")
def rules(current: User = Depends(get_current_user)):
    hf = [r.dict() for r in _rules.list_rules() if "happy_flow" in r.tags]
    by_dataset: dict[str, list] = {}
    for r in hf:
        by_dataset.setdefault(r["source_dataset"], []).append({"indicator_id": r["indicator_id"], "name": r["name"]})
    return {"aantal": len(hf), "per_dataset": by_dataset}


@router.post("/datastation/laad-testset")
def laad_testset(current: User = Depends(get_current_user)):
    """Laad de meegeleverde demo-testset: brondata → concepten → RDF in de store."""
    cfg = json.loads((_DEMO_DIR / "mapping.json").read_text())
    df = pd.read_csv(_DEMO_DIR / cfg["dataset"])
    records = df.to_dict("records")
    n_triples = STATION.laad_dataset(cfg["dataset"], records, cfg["mapping"], cfg.get("class_uri"))
    return {"status": "ok", "dataset": cfg["dataset"], "records": len(records),
            "triples": n_triples, "store_triples": STATION.triple_count}


@router.post("/datastation/upload")
async def upload(file: UploadFile = File(...), mapping: str = Form(...),
                 class_uri: str | None = Form(default=None),
                 current: User = Depends(get_current_user)):
    """Echte brondata inladen: CSV/XML + kolom→concept-mapping (JSON)."""
    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as exc:
        raise HTTPException(422, f"Kon bestand niet lezen als CSV: {exc}")
    try:
        m = json.loads(mapping)
    except Exception as exc:
        raise HTTPException(422, f"Ongeldige mapping-JSON: {exc}")
    records = df.to_dict("records")
    n = STATION.laad_dataset(file.filename, records, m, class_uri)
    return {"status": "ok", "dataset": file.filename, "records": len(records), "triples": n}


@router.post("/datastation/beantwoord")
def beantwoord(vraag: SparqlVraag, current: User = Depends(get_current_user)):
    """Beantwoord een gevalideerde vraag (SPARQL) op de ingeladen store."""
    a = STATION.beantwoord(vraag.sparql)
    return {"status": a.status, "waarde": a.waarde, "backend": a.backend, "toelichting": a.toelichting}


@router.post("/datastation/reset")
def reset(current: User = Depends(get_current_user)):
    STATION.reset()
    return {"status": "ok"}
