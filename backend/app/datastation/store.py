"""
store.py — De RDF-store van het datastation.

Houdt een master-graph bij van alle ingeladen datasets (brondata → concepten → RDF)
en beantwoordt gevalideerde SPARQL-vragen, primair via Fuseki met rdflib-fallback.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from . import rdf_store as rs


def _kies_waarde(cols, rows):
    """Kies de uitkomst: prefereer een kolom 'waarde', anders de eerste scalar."""
    if not rows:
        return None
    for key in ("waarde", "value", "result"):
        if key in cols and rows[0].get(key) not in (None, ""):
            try:
                return float(str(rows[0][key]).replace(",", "."))
            except (TypeError, ValueError):
                pass
    return rs._first_scalar(cols, rows)


@dataclass
class Antwoord:
    status: str                 # OK | GEEN_DATA | FOUT
    waarde: Optional[float]
    backend: str                # fuseki | rdflib
    toelichting: Optional[str] = None


class Datastation:
    """In-memory master-graph + ingeladen datasets (per processtart)."""

    def __init__(self) -> None:
        self._graph = None        # rdflib.Graph
        self._datasets: dict[str, int] = {}   # naam -> aantal records

    def reset(self) -> None:
        self._graph = None
        self._datasets = {}

    def laad_dataset(self, naam: str, records: list[dict], mapping: dict,
                     class_uri: Optional[str] = None, id_field: Optional[str] = None) -> int:
        from rdflib import Graph
        g = rs.build_graph(records, mapping, class_uri, id_field=id_field)
        if self._graph is None:
            self._graph = Graph()
            for pre, ns in g.namespaces():
                self._graph.bind(pre, ns)
        for t in g:
            self._graph.add(t)
        self._datasets[naam] = len(records)
        return len(g)

    def laad_graph(self, naam: str, graph, n_records: int) -> int:
        from rdflib import Graph
        if self._graph is None:
            self._graph = Graph()
            for pre, ns in graph.namespaces():
                self._graph.bind(pre, ns)
        for t in graph:
            self._graph.add(t)
        self._datasets[naam] = n_records
        return len(graph)

    @property
    def triple_count(self) -> int:
        return len(self._graph) if self._graph is not None else 0

    @property
    def datasets(self) -> dict[str, int]:
        return dict(self._datasets)

    def beantwoord(self, sparql: str) -> Antwoord:
        if self._graph is None or len(self._graph) == 0:
            return Antwoord("GEEN_DATA", None, "rdflib", "Geen data ingeladen in het datastation")
        # primair Fuseki
        if rs.FUSEKI_URL:
            try:
                rs._fuseki_load(self._graph)
                cols, rows = rs._fuseki_query(sparql)
                val = _kies_waarde(cols, rows)
                return Antwoord("OK" if val is not None else "GEEN_DATA", val, "fuseki")
            except Exception:
                pass
        # fallback rdflib
        try:
            res = self._graph.query(sparql)
            cols, rows = rs._parse_rdflib_result(res)
            val = _kies_waarde(cols, rows)
            return Antwoord("OK" if val is not None else "GEEN_DATA", val, "rdflib")
        except Exception as exc:
            return Antwoord("FOUT", None, "rdflib", f"SPARQL-fout: {exc}")


# Eén datastation per proces
STATION = Datastation()


def seed_twin(codes=None) -> None:
    """Twin-demo: kik:Observatie-data zodat de gevalideerde vraag vanuit Uitvraag
    (AVG over kik:waarde per kik:indicator) een echt antwoord oplevert. Idempotent."""
    import hashlib
    from rdflib import Graph, Literal, Namespace, URIRef
    from rdflib.namespace import RDF, XSD
    if STATION.triple_count > 0:
        return
    if codes is None:
        codes = ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7",
                 "2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7",
                 "3.1", "3.2", "3.3",
                 "PERS_RATIO", "ZIEKTEVERZUIM", "MEDEWERKERS", "CLIENT_TEVREDENHEID"]
    KIK = Namespace("https://kik-v.nl/ns#")
    g = Graph(); g.bind("kik", KIK)
    i = 0; n = 0
    for code in codes:
        h = int(hashlib.sha256(code.encode()).hexdigest(), 16)
        for k in range(4):
            v = round(((h >> (k * 7)) % 1000) / 10.0 + 5, 1)
            node = URIRef(f"http://rhadix.nl/twin/o{i}"); i += 1; n += 1
            g.add((node, RDF.type, KIK.Observatie))
            g.add((node, KIK.indicator, Literal(code)))                 # plain literal
            g.add((node, KIK.waarde, Literal(v, datatype=XSD.decimal)))
    STATION.laad_graph("twin_observaties", g, n)
