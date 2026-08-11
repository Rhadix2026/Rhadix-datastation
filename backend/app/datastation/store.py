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
        _SEEDED_CODES.clear()

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


# Reeds geseede indicator-codes (procesniveau, idempotent over aanroepen heen).
# Wordt geleegd bij Datastation.reset().
_SEEDED_CODES: set[str] = set()


def _seed_observaties(codes) -> int:
    """Voeg idempotent kik:Observatie-demodata toe voor de gegeven indicator-codes.

    Elke code krijgt 4 deterministische observaties; de gevalideerde vraag vanuit
    Uitvraag (AVG over kik:waarde per kik:indicator) levert daarmee een antwoord op.
    Al geseede codes worden overgeslagen; de node-URI's zijn deterministisch, dus
    herhaald seeden is sowieso lossless."""
    import hashlib
    from rdflib import Graph, Literal, Namespace, URIRef
    from rdflib.namespace import RDF, XSD
    nieuw = [c for c in dict.fromkeys(codes) if c and c not in _SEEDED_CODES]
    if not nieuw:
        return 0
    KIK = Namespace("https://kik-v.nl/ns#")
    g = Graph(); g.bind("kik", KIK)
    n = 0
    for code in nieuw:
        h = int(hashlib.sha256(str(code).encode()).hexdigest(), 16)
        safe = "".join(ch if ch.isalnum() else "_" for ch in str(code))
        for k in range(4):
            v = round(((h >> (k * 7)) % 1000) / 10.0 + 5, 1)
            node = URIRef(f"http://rhadix.nl/twin/o_{safe}_{k}")
            g.add((node, RDF.type, KIK.Observatie))
            g.add((node, KIK.indicator, Literal(code)))                 # plain literal
            g.add((node, KIK.waarde, Literal(v, datatype=XSD.decimal)))
        _SEEDED_CODES.add(code)
        n += 4
    STATION.laad_graph("twin_observaties", g, len(_SEEDED_CODES) * 4)
    return n


def seed_twin(codes=None) -> None:
    """Twin-demo bij opstart: basis kik:Observatie-data zodat een gevalideerde vraag
    vanuit Uitvraag een antwoord oplevert. Idempotent. Codes buiten deze basisset
    worden lazy bijgeseed zodra ze binnenkomen (zie zorg_voor_observatie)."""
    if codes is None:
        codes = ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7",
                 "2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7",
                 "3.1", "3.2", "3.3",
                 "PERS_RATIO", "ZIEKTEVERZUIM", "MEDEWERKERS", "CLIENT_TEVREDENHEID"]
    _seed_observaties(codes)


def zorg_voor_observatie(code) -> None:
    """Lazy seeding: zorg dat er kik:Observatie-demodata bestaat voor deze
    indicator-code, ongeacht welk uitwisselprofiel de afnemer gebruikt. Idempotent.
    Hiermee levert elke indicator die Uitvraag kan sturen een waarde op i.p.v. 0."""
    if code:
        _seed_observaties([code])
