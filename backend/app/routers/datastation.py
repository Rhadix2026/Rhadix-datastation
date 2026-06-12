"""datastation.py — API van het Rhadix Datastation."""
from __future__ import annotations

import io
import json
import pathlib

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import datastation_models as dm

from app.auth.dependencies import get_current_user
from app.models.auth_models import User
from app.datastation import rdf_store
from app.datastation.store import STATION
from app.datastation.rule_engine import RuleEngine
from app.datastation import happyflow as hf

router = APIRouter(tags=["datastation"])

_DEMO_DIR = pathlib.Path(__file__).parent.parent / "datastation" / "demo"
_RULES_DIR = pathlib.Path(__file__).parent.parent / "datastation" / "rules"

_rules = RuleEngine()
if _RULES_DIR.exists():
    _rules.load_directory(_RULES_DIR)

# In-memory cache van de laatst geladen happy-flow brondata (voor het overzicht).
_HF_DATA: dict[str, list[dict]] = {}


def _happy_flow_rules() -> list[dict]:
    return [r.dict() for r in _rules.list_rules() if "happy_flow" in r.tags]



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
def beantwoord(vraag: SparqlVraag):
    # Publiek/server-to-server: een afnemer (Uitvraag) stuurt de gevalideerde vraag.
    # (KIK-V-vertrouwenslaag — Verifiable Credential-verificatie — is fase 3.)
    """Beantwoord een gevalideerde vraag (SPARQL) op de ingeladen store."""
    a = STATION.beantwoord(vraag.sparql)
    return {"status": a.status, "waarde": a.waarde, "backend": a.backend, "toelichting": a.toelichting}


@router.post("/datastation/laad-happyflow")
def laad_happyflow(current: User = Depends(get_current_user)):
    """Laad de ingebouwde happy-flow testset: alle datasets -> concepten -> RDF.

    Eén coherente fictieve zorgaanbieder over alle referentieontwerpen.
    """
    global _HF_DATA
    _HF_DATA = hf.genereer_alles()
    geladen = []
    totaal = 0
    for d in hf.DATASETS:
        records = _HF_DATA[d.naam]
        n = STATION.laad_dataset(d.naam, records, d.mapping, d.class_uri, id_field=d.id_field)
        totaal += n
        geladen.append({"dataset": d.naam, "records": len(records), "triples": n})
    return {"status": "ok", "datasets": geladen,
            "store_triples": STATION.triple_count, "nieuwe_triples": totaal}


@router.get("/datastation/happyflow-overzicht")
def happyflow_overzicht(current: User = Depends(get_current_user)):
    """Per indicator: validatie-berekening (brondata) vs datastation-antwoord (SPARQL)."""
    data = _HF_DATA or hf.genereer_alles()
    per_dataset: dict[str, list] = {}
    n_match = n_totaal = 0
    for r in _happy_flow_rules():
        ds = r["source_dataset"]
        ref = hf.referentie_for_rule(r, data.get(ds, []))
        q = hf.sparql_for_rule(r)
        ds_waarde = None
        if q is not None:
            a = STATION.beantwoord(q)
            ds_waarde = a.waarde
        if ds_waarde is not None:
            ds_waarde = round(float(ds_waarde), 2)
        geladen = bool(_HF_DATA)
        match = (geladen and ref is not None and ds_waarde is not None
                 and abs(ref - ds_waarde) < 0.01)
        n_totaal += 1
        if match:
            n_match += 1
        agg = r.get("aggregation", {})
        per_dataset.setdefault(ds, []).append({
            "indicator_id": r["indicator_id"],
            "name": r.get("name"),
            "aggregatie": f"{agg.get('function')}({agg.get('field') or ''})",
            "validatie": ref,
            "datastation": ds_waarde if geladen else None,
            "match": match,
        })
    return {"geladen": bool(_HF_DATA), "aantal": n_totaal, "match": n_match,
            "per_dataset": per_dataset}


# ── Vraag-inbox (asynchrone, beoordeelde beantwoording) ───────────────────────
class VraagIn(BaseModel):
    sparql: str
    uitwisselprofiel: str | None = None
    indicator_code: str | None = None
    afnemer: str | None = None
    zorgaanbieder: str | None = None


class OverschrijfIn(BaseModel):
    waarde: float
    toelichting: str | None = None


class AfwijzenIn(BaseModel):
    reden: str | None = None


def _audit(db: Session, vraag_id, actie: str, details: str | None = None, door: str | None = None) -> None:
    db.add(dm.DatastationAudit(vraag_id=vraag_id, actie=actie, details=details, door=door))


@router.post("/datastation/vragen", status_code=201)
def vraag_indienen(body: VraagIn, db: Session = Depends(get_db)):
    """Publiek/server-to-server: een afnemer (Uitvraag) dient een gevalideerde
    vraag in. Het datastation berekent meteen een voorstel-antwoord; dit wacht
    vervolgens op beoordeling door de zorgaanbieder voordat het wordt verzonden."""
    vraag = dm.DatastationVraag(
        sparql=body.sparql, uitwisselprofiel=body.uitwisselprofiel,
        indicator_code=body.indicator_code, afnemer=body.afnemer,
        zorgaanbieder=body.zorgaanbieder, status=dm.STATUS_TE_BEOORDELEN,
    )
    db.add(vraag)
    db.flush()
    _audit(db, vraag.id, "ONTVANGEN", f"afnemer={body.afnemer or '-'}")
    a = STATION.beantwoord(body.sparql)
    vraag.backend = a.backend
    if a.status == "OK" and a.waarde is not None:
        vraag.berekende_waarde = round(float(a.waarde), 4)
        _audit(db, vraag.id, "BEREKEND", f"waarde={vraag.berekende_waarde} ({a.backend})")
    else:
        vraag.status = dm.STATUS_FOUT
        vraag.toelichting = a.toelichting or "Geen waarde berekend"
        _audit(db, vraag.id, "BEREKEND", f"status={a.status}: {vraag.toelichting}")
    db.commit()
    db.refresh(vraag)
    return vraag.as_dict()


@router.get("/datastation/vragen")
def vragen_lijst(status: str = "open", db: Session = Depends(get_db),
                 current: User = Depends(get_current_user)):
    """Inbox. status=open (te beoordelen+fout), verzonden, afgewezen of alle."""
    q = db.query(dm.DatastationVraag)
    if status == "open":
        q = q.filter(dm.DatastationVraag.status.in_([dm.STATUS_TE_BEOORDELEN, dm.STATUS_FOUT]))
    elif status == "verzonden":
        q = q.filter(dm.DatastationVraag.status == dm.STATUS_VERZONDEN)
    elif status == "afgewezen":
        q = q.filter(dm.DatastationVraag.status == dm.STATUS_AFGEWEZEN)
    items = q.order_by(dm.DatastationVraag.ontvangen_op.desc()).all()
    return {"aantal": len(items), "vragen": [v.as_dict() for v in items]}


@router.get("/datastation/vragen/stats")
def vragen_stats(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    from sqlalchemy import func as f
    rows = db.query(dm.DatastationVraag.status, f.count()).group_by(dm.DatastationVraag.status).all()
    per = {s: n for s, n in rows}
    return {
        "te_beoordelen": per.get(dm.STATUS_TE_BEOORDELEN, 0),
        "verzonden": per.get(dm.STATUS_VERZONDEN, 0),
        "afgewezen": per.get(dm.STATUS_AFGEWEZEN, 0),
        "fout": per.get(dm.STATUS_FOUT, 0),
    }


@router.post("/datastation/vragen/accordeer-alles")
def accorderen_alles(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    """Accordeer in één keer alle te-beoordelen vragen met een berekend antwoord."""
    from sqlalchemy.sql import func as f
    vs = (db.query(dm.DatastationVraag)
          .filter(dm.DatastationVraag.status == dm.STATUS_TE_BEOORDELEN,
                  dm.DatastationVraag.berekende_waarde.isnot(None))
          .all())
    n = 0
    for v in vs:
        v.definitieve_waarde = v.berekende_waarde
        v.handmatig = False
        v.status = dm.STATUS_VERZONDEN
        v.beoordeeld_op = f.now()
        v.beoordeeld_door = current.email
        _audit(db, v.id, "GEACCORDEERD", f"waarde={v.definitieve_waarde} (bulk)", current.email)
        n += 1
    db.commit()
    return {"geaccordeerd": n}


def _get_vraag(db: Session, vraag_id: str) -> "dm.DatastationVraag":
    v = db.query(dm.DatastationVraag).filter(dm.DatastationVraag.id == vraag_id).first()
    if not v:
        raise HTTPException(404, "Vraag niet gevonden")
    return v


@router.get("/datastation/vragen/{vraag_id}")
def vraag_detail(vraag_id: str, db: Session = Depends(get_db),
                 current: User = Depends(get_current_user)):
    v = _get_vraag(db, vraag_id)
    d = v.as_dict()
    d["audit"] = [a.as_dict() for a in v.audit]
    return d


@router.post("/datastation/vragen/{vraag_id}/accordeer")
def vraag_accorderen(vraag_id: str, db: Session = Depends(get_db),
                     current: User = Depends(get_current_user)):
    from sqlalchemy.sql import func as f
    v = _get_vraag(db, vraag_id)
    if v.status not in (dm.STATUS_TE_BEOORDELEN,):
        raise HTTPException(409, f"Vraag is niet te beoordelen (status {v.status})")
    if v.berekende_waarde is None:
        raise HTTPException(409, "Geen berekend antwoord om te accorderen")
    v.definitieve_waarde = v.berekende_waarde
    v.handmatig = False
    v.status = dm.STATUS_VERZONDEN
    v.beoordeeld_op = f.now()
    v.beoordeeld_door = current.email
    _audit(db, v.id, "GEACCORDEERD", f"waarde={v.definitieve_waarde}", current.email)
    db.commit(); db.refresh(v)
    return v.as_dict()


@router.post("/datastation/vragen/{vraag_id}/overschrijf")
def vraag_overschrijven(vraag_id: str, body: OverschrijfIn, db: Session = Depends(get_db),
                        current: User = Depends(get_current_user)):
    from sqlalchemy.sql import func as f
    v = _get_vraag(db, vraag_id)
    if v.status not in (dm.STATUS_TE_BEOORDELEN, dm.STATUS_FOUT):
        raise HTTPException(409, f"Vraag is niet te beoordelen (status {v.status})")
    v.definitieve_waarde = round(float(body.waarde), 4)
    v.handmatig = True
    v.toelichting = body.toelichting
    v.status = dm.STATUS_VERZONDEN
    v.beoordeeld_op = f.now()
    v.beoordeeld_door = current.email
    _audit(db, v.id, "OVERSCHREVEN",
           f"waarde={v.definitieve_waarde}; reden={body.toelichting or '-'}", current.email)
    db.commit(); db.refresh(v)
    return v.as_dict()


@router.post("/datastation/vragen/{vraag_id}/wijs-af")
def vraag_afwijzen(vraag_id: str, body: AfwijzenIn, db: Session = Depends(get_db),
                   current: User = Depends(get_current_user)):
    from sqlalchemy.sql import func as f
    v = _get_vraag(db, vraag_id)
    if v.status == dm.STATUS_VERZONDEN:
        raise HTTPException(409, "Reeds verzonden vraag kan niet worden afgewezen")
    v.status = dm.STATUS_AFGEWEZEN
    v.toelichting = body.reden
    v.beoordeeld_op = f.now()
    v.beoordeeld_door = current.email
    _audit(db, v.id, "AFGEWEZEN", body.reden or "-", current.email)
    db.commit(); db.refresh(v)
    return v.as_dict()


@router.get("/datastation/vragen/{vraag_id}/resultaat")
def vraag_resultaat(vraag_id: str, db: Session = Depends(get_db)):
    """Publiek: de afnemer haalt het resultaat op. Pas beschikbaar na verzending."""
    v = _get_vraag(db, vraag_id)
    if v.status == dm.STATUS_VERZONDEN:
        _audit(db, v.id, "OPGEHAALD", f"afnemer={v.afnemer or '-'}")
        db.commit()
        return {"query_id": str(v.id), "status": "GEREED",
                "waarde": v.definitieve_waarde, "handmatig": v.handmatig,
                "toelichting": v.toelichting, "zaaknummer": str(v.id)}
    if v.status == dm.STATUS_AFGEWEZEN:
        return {"query_id": str(v.id), "status": "AFGEWEZEN", "toelichting": v.toelichting}
    return {"query_id": str(v.id), "status": "IN_BEHANDELING"}


@router.post("/datastation/reset")
def reset(current: User = Depends(get_current_user)):
    STATION.reset()
    return {"status": "ok"}
