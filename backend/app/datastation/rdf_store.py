"""
rdf_store.py — Rhadix Reconciliation Engine
============================================
"Loslaten van SPARQL op de data."

Pijplijn:
  1. Brondata (CSV/Excel/AFAS-XML) → pandas DataFrame  (zie calculation_engine)
  2. Handmatige kolom→concept mapping → RDF-triples (rdflib Graph)
  3. Triples laden in een triple store:
        - primair : Apache Jena Fuseki  (env FUSEKI_URL)
        - fallback: rdflib in-memory    (geen externe service nodig)
  4. Geselecteerde SPARQL-query uitvoeren tegen de store
  5. Resultaat (bindings + scalaire uitkomst) teruggeven

De mapping wordt door de gebruiker in de UI opgegeven en heeft per kolom:
    {
      "concept_uri": "http://purl.org/ozo/onz-g#personeelsnummer",
      "kind":        "literal" | "resource",   # default literal
      "datatype":    "string" | "date" | "decimal" | "integer" | "boolean"
    }
Kolommen zonder mapping worden genegeerd.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional

import requests

try:
    from rdflib import BNode, Graph, Literal, Namespace, URIRef
    from rdflib.namespace import RDF, XSD
    _RDFLIB = True
except ImportError:  # pragma: no cover - rdflib staat in requirements
    _RDFLIB = False


# ── Configuratie ──────────────────────────────────────────────────────────────
FUSEKI_URL = os.getenv("FUSEKI_URL", "").rstrip("/")          # bv. http://fuseki:3030
FUSEKI_DATASET = os.getenv("FUSEKI_DATASET", "rhadix")
FUSEKI_USER = os.getenv("FUSEKI_USER", "")
FUSEKI_PASSWORD = os.getenv("FUSEKI_PASSWORD", "")
FUSEKI_TIMEOUT = int(os.getenv("FUSEKI_TIMEOUT", "30"))

# Namespace voor de gegenereerde record-nodes (instances uit de brondata)
RECORD_NS = "http://rhadix.nl/recon/resource/"

# Datatype-keuze in de UI → XSD-URI
_XSD_MAP = {
    "string": "http://www.w3.org/2001/XMLSchema#string",
    "date": "http://www.w3.org/2001/XMLSchema#date",
    "datetime": "http://www.w3.org/2001/XMLSchema#dateTime",
    "decimal": "http://www.w3.org/2001/XMLSchema#decimal",
    "integer": "http://www.w3.org/2001/XMLSchema#integer",
    "boolean": "http://www.w3.org/2001/XMLSchema#boolean",
}

_DATE_DDMMYYYY = re.compile(r"^(\d{2})[-/](\d{2})[-/](\d{4})$")
_DATE_YYYYMMDD_COMPACT = re.compile(r"^(\d{4})(\d{2})(\d{2})$")


# ── Resultaat-containers ──────────────────────────────────────────────────────
@dataclass
class SparqlRunResult:
    backend: str                       # "fuseki" of "rdflib"
    columns: list[str]
    rows: list[dict]
    scalar: float | None               # eerste numerieke waarde in eerste rij
    triple_count: int
    fuseki_error: str | None = None    # gevuld als Fuseki faalde en fallback gebruikt is
    query_error: str | None = None

    def to_dict(self) -> dict:
        return {
            "backend": self.backend,
            "columns": self.columns,
            "rows": self.rows,
            "scalar": self.scalar,
            "triple_count": self.triple_count,
            "fuseki_error": self.fuseki_error,
            "query_error": self.query_error,
        }


# ── Stap 1: waarde-normalisatie ───────────────────────────────────────────────
def _normalize_date(val: str) -> str:
    """Zet dd-mm-jjjj of jjjjmmdd om naar ISO (jjjj-mm-dd) voor xsd:date."""
    s = val.strip()
    m = _DATE_DDMMYYYY.match(s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    m = _DATE_YYYYMMDD_COMPACT.match(s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    # 2026-04-19T00:00:00 → 2026-04-19
    if "T" in s and len(s) >= 10:
        return s[:10]
    return s


def _make_literal(value: Any, datatype: str | None):
    """Bouw een rdflib Literal met optioneel XSD-datatype."""
    sval = "" if value is None else str(value).strip()
    if sval == "":
        return None
    dt = (datatype or "string").lower()
    if dt in ("date", "datetime"):
        iso = _normalize_date(sval)
        return Literal(iso, datatype=URIRef(_XSD_MAP[dt]))
    if dt in ("decimal", "integer"):
        # Europese notatie: "1.234,50" → "1234.50", "1234,50" → "1234.50"
        if "," in sval and "." in sval:
            cleaned = sval.replace(".", "").replace(",", ".")
        else:
            cleaned = sval.replace(",", ".")
        try:
            num = float(cleaned)
            if dt == "integer":
                return Literal(int(num), datatype=URIRef(_XSD_MAP["integer"]))
            return Literal(num, datatype=URIRef(_XSD_MAP["decimal"]))
        except ValueError:
            return Literal(sval)  # val terug op plain literal
    if dt == "boolean":
        return Literal(sval.lower() in ("true", "1", "ja", "yes", "waar"),
                       datatype=URIRef(_XSD_MAP["boolean"]))
    return Literal(sval, datatype=URIRef(_XSD_MAP["string"]))


def _safe_local(value: str) -> str:
    """Maak een URI-veilig fragment van een identifier-waarde."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(value).strip()) or "x"


# ── Stap 2: DataFrame + mapping → rdflib Graph ────────────────────────────────
def build_graph(
    records: list[dict],
    mapping: dict[str, dict],
    class_uri: str | None,
    id_field: str | None = None,
    max_rows: int = 50000,
) -> "Graph":
    """
    Bouw een rdflib Graph uit brondata-records en een handmatige mapping.

    records   : list van dicts (één per rij, kolomnaam → waarde)
    mapping   : {kolomnaam: {concept_uri, kind, datatype}}
    class_uri : rdf:type voor elke record-node (optioneel)
    id_field  : kolom waarvan de waarde de node-URI bepaalt (optioneel)
    """
    if not _RDFLIB:
        raise RuntimeError("rdflib is niet geïnstalleerd — voeg toe aan requirements.")

    g = Graph()
    g.bind("onz-g", Namespace("http://purl.org/ozo/onz-g#"))
    g.bind("onz-pers", Namespace("http://purl.org/ozo/onz-pers#"))
    g.bind("onz-org", Namespace("http://purl.org/ozo/onz-org#"))
    g.bind("onz-fin", Namespace("http://purl.org/ozo/onz-fin#"))
    g.bind("onz-zorg", Namespace("http://purl.org/ozo/onz-zorg#"))
    g.bind("rec", Namespace(RECORD_NS))

    # alleen kolommen met een geldige concept_uri tellen mee
    active = {
        col: cfg
        for col, cfg in (mapping or {}).items()
        if isinstance(cfg, dict) and cfg.get("concept_uri")
    }

    class_ref = URIRef(class_uri) if class_uri else None

    for idx, row in enumerate(records[:max_rows]):
        # node-URI: op basis van id_field-waarde, anders rij-index
        if id_field and row.get(id_field) not in (None, ""):
            node = URIRef(RECORD_NS + _safe_local(row[id_field]))
        else:
            node = URIRef(RECORD_NS + f"r{idx}")

        if class_ref is not None:
            g.add((node, RDF.type, class_ref))

        for col, cfg in active.items():
            if col not in row:
                continue
            val = row[col]
            pred = URIRef(cfg["concept_uri"])
            kind = (cfg.get("kind") or "literal").lower()
            if kind == "resource":
                sval = "" if val is None else str(val).strip()
                if not sval:
                    continue
                obj = URIRef(sval) if sval.startswith("http") else URIRef(RECORD_NS + _safe_local(sval))
                g.add((node, pred, obj))
            else:
                lit = _make_literal(val, cfg.get("datatype"))
                if lit is not None:
                    g.add((node, pred, lit))

    return g


# ── Stap 3+4: SPARQL-resultaat parsen ─────────────────────────────────────────
def _coerce_number(s: str):
    try:
        if re.fullmatch(r"-?\d+", s):
            return int(s)
        return float(s)
    except (ValueError, TypeError):
        return None


def _first_scalar(columns: list[str], rows: list[dict]) -> float | None:
    """Pak de eerste numerieke waarde uit de eerste resultaatrij."""
    if not rows:
        return None
    first = rows[0]
    for col in columns:
        num = _coerce_number(str(first.get(col, "")))
        if num is not None:
            return float(num)
    return None


def _parse_fuseki_json(payload: dict) -> tuple[list[str], list[dict]]:
    vars_ = payload.get("head", {}).get("vars", [])
    bindings = payload.get("results", {}).get("bindings", [])
    rows = []
    for b in bindings:
        rows.append({v: (b.get(v, {}) or {}).get("value", "") for v in vars_})
    return vars_, rows


def _parse_rdflib_result(result) -> tuple[list[str], list[dict]]:
    vars_ = [str(v) for v in (result.vars or [])]
    rows = []
    for r in result:
        row = {}
        for v in vars_:
            val = r[v] if hasattr(r, "__getitem__") else None
            row[v] = "" if val is None else str(val)
        rows.append(row)
    return vars_, rows


# ── Fuseki-client ─────────────────────────────────────────────────────────────
def _fuseki_auth():
    if FUSEKI_USER:
        return (FUSEKI_USER, FUSEKI_PASSWORD)
    return None


def _fuseki_load(graph: "Graph") -> None:
    """Vervang de default graph in de Fuseki-dataset met deze triples (Graph Store Protocol)."""
    turtle = graph.serialize(format="turtle")
    if isinstance(turtle, bytes):
        turtle = turtle.decode("utf-8")
    url = f"{FUSEKI_URL}/{FUSEKI_DATASET}/data?default"
    resp = requests.put(
        url,
        data=turtle.encode("utf-8"),
        headers={"Content-Type": "text/turtle"},
        auth=_fuseki_auth(),
        timeout=FUSEKI_TIMEOUT,
    )
    resp.raise_for_status()


def _fuseki_query(sparql: str) -> tuple[list[str], list[dict]]:
    url = f"{FUSEKI_URL}/{FUSEKI_DATASET}/query"
    resp = requests.post(
        url,
        data={"query": sparql},
        headers={"Accept": "application/sparql-results+json"},
        auth=_fuseki_auth(),
        timeout=FUSEKI_TIMEOUT,
    )
    resp.raise_for_status()
    return _parse_fuseki_json(resp.json())


def fuseki_available() -> bool:
    """Snelle ping om te zien of Fuseki bereikbaar is."""
    if not FUSEKI_URL:
        return False
    try:
        resp = requests.get(f"{FUSEKI_URL}/$/ping", timeout=3, auth=_fuseki_auth())
        return resp.status_code < 500
    except Exception:
        return False


# ── Stap 5: orkestratie ───────────────────────────────────────────────────────
def run_sparql_on_records(
    records: list[dict],
    mapping: dict[str, dict],
    sparql: str,
    class_uri: str | None = None,
    id_field: str | None = None,
    prefer_fuseki: bool = True,
) -> SparqlRunResult:
    """
    Bouw triples uit de brondata + mapping, laad ze in de triple store en
    voer de SPARQL-query uit. Probeert eerst Fuseki, valt terug op rdflib.
    """
    graph = build_graph(records, mapping, class_uri, id_field=id_field)
    triple_count = len(graph)

    fuseki_error: str | None = None

    # ── Primair: Fuseki ──────────────────────────────────────────────────────
    if prefer_fuseki and FUSEKI_URL:
        try:
            _fuseki_load(graph)
            cols, rows = _fuseki_query(sparql)
            return SparqlRunResult(
                backend="fuseki",
                columns=cols,
                rows=rows,
                scalar=_first_scalar(cols, rows),
                triple_count=triple_count,
            )
        except Exception as exc:
            fuseki_error = str(exc)

    # ── Fallback: rdflib in-memory ───────────────────────────────────────────
    try:
        result = graph.query(sparql)
        cols, rows = _parse_rdflib_result(result)
        return SparqlRunResult(
            backend="rdflib",
            columns=cols,
            rows=rows,
            scalar=_first_scalar(cols, rows),
            triple_count=triple_count,
            fuseki_error=fuseki_error,
        )
    except Exception as exc:
        return SparqlRunResult(
            backend="rdflib",
            columns=[],
            rows=[],
            scalar=None,
            triple_count=triple_count,
            fuseki_error=fuseki_error,
            query_error=str(exc),
        )
