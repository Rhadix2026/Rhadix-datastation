"""
store.py — De RDF-store van het datastation.

Houdt een master-graph bij van alle ingeladen datasets (brondata → concepten → RDF)
en beantwoordt gevalideerde SPARQL-vragen, primair via Fuseki met rdflib-fallback.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from . import rdf_store as rs


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
                val = rs._first_scalar(cols, rows)
                return Antwoord("OK" if val is not None else "GEEN_DATA", val, "fuseki")
            except Exception:
                pass
        # fallback rdflib
        try:
            res = self._graph.query(sparql)
            cols, rows = rs._parse_rdflib_result(res)
            val = rs._first_scalar(cols, rows)
            return Antwoord("OK" if val is not None else "GEEN_DATA", val, "rdflib")
        except Exception as exc:
            return Antwoord("FOUT", None, "rdflib", f"SPARQL-fout: {exc}")


# Eén datastation per proces
STATION = Datastation()
