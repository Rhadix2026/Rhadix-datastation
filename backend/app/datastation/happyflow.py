"""
happyflow.py — Rhadix Datastation
=================================
De *ingebouwde* happy-flow testset van de digital twin.

Doel: één coherente, fictieve zorgaanbieder met brondata over alle KIK-V
referentieontwerpen (cliënten, medewerkers, vestigingen, financieel, AFAS Profit).
De data wordt deterministisch gegenereerd (vaste seed), per dataset naar
KIK-V-concepten (onz-*) gemapt, als RDF in de datastation-store geladen en
vervolgens met SPARQL bevraagd.

Voor elke happy-flow indicator (uit `rules/`) tonen we twee getallen:
  • validatie  — de aggregatie rechtstreeks op de brondata (pandas-semantiek);
  • datastation — hetzelfde antwoord, maar via SPARQL op de RDF-store.
Kloppen ze, dan is de keten "data → concepten → RDF → gevalideerde vraag" rond.

De synthetische getallen zijn fictief; de échte KIK-V happy-flow bestanden kun
je later via de upload-knop in dezelfde store laden — de pijplijn blijft gelijk.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Callable

# -- Namespaces ---------------------------------------------------------------
ONZ_G = "http://purl.org/ozo/onz-g#"
ONZ_PERS = "http://purl.org/ozo/onz-pers#"
ONZ_ORG = "http://purl.org/ozo/onz-org#"
ONZ_FIN = "http://purl.org/ozo/onz-fin#"
ONZ_ZORG = "http://purl.org/ozo/onz-zorg#"


def _S(uri: str, kind: str = "literal", datatype: str = "string") -> dict:
    return {"concept_uri": uri, "kind": kind, "datatype": datatype}


@dataclass
class DatasetDef:
    naam: str
    class_uri: str
    id_field: str | None
    mapping: dict
    generate: Callable[[random.Random], list]


# -- Generators (deterministisch) ---------------------------------------------
N_MED = 150
N_CLIENT = 210
REGIOS = ["Noord", "Oost", "Zuid", "West"]
WLZ_PROFIELEN = [f"VV{i}" for i in range(4, 11)]
FUNCTIES = ["Verzorgende IG", "Verpleegkundige", "Helpende", "Begeleider",
            "Teamleider", "Activiteitenbegeleider", "Huishoudelijke hulp",
            "Gastvrouw", "Behandelaar", "Kwaliteitsmedewerker"]


def _emp_ids(n: int) -> list:
    return [f"M{idx:04d}" for idx in range(1, n + 1)]


def gen_client_ons(r):
    return [{"objectId": f"C{idx:05d}", "wlzProfiel": r.choice(WLZ_PROFIELEN)}
            for idx in range(1, N_CLIENT + 1)]


def gen_medewerker_ons(r):
    return [{"identificationNo": mid} for mid in _emp_ids(N_MED)]


def gen_medewerker_afas(r):
    return [{"PersoneelsNummer": f"P{idx:05d}"} for idx in range(1, N_MED + 1)]


def gen_vestiging_ons(r):
    return [{"objectId": f"V{idx:03d}", "regio": REGIOS[idx % len(REGIOS)]}
            for idx in range(8)]


def gen_functie_ons(r):
    return [{"functie": r.choice(FUNCTIES)} for _ in range(N_MED)]


def gen_financieel(r):
    gbr = [f"4{n:03d}" for n in range(60)]
    return [{"grootBoekRekening": r.choice(gbr),
             "boekingsBedrag": round(r.uniform(-2500, 7500), 2)} for _ in range(480)]


def gen_grootboekrubriek(r):
    return [{"grootboekRekeningNummer": f"4{n:03d}"} for n in range(60)]


def gen_kostenplaats(r):
    return [{"kostenPlaats": f"KP{n:03d}"} for n in range(24)]


def gen_verzuim_ons(r):
    meds = _emp_ids(N_MED)
    return [{"employeeId": r.choice(meds)} for _ in range(96)]


def gen_verzuim_afas(r):
    return [{"PersoneelsNummer": f"P{r.randint(1, N_MED):05d}"} for _ in range(96)]


def gen_werkovereenkomst_afas(r):
    return [{"DienstverbandNummer": f"DV{idx:05d}",
             "PersoneelsNummer": f"P{r.randint(1, N_MED):05d}"} for idx in range(1, 166)]


def gen_werkovereenkomst_ons(r):
    meds = _emp_ids(N_MED)
    return [{"objectId": f"WO{idx:05d}", "employeeId": r.choice(meds)} for idx in range(1, 166)]


def gen_profit_employees(r):
    rows = []
    for mid in _emp_ids(N_MED):
        eind = "" if r.random() > 0.12 else f"2025-{r.randint(1,12):02d}-15"
        rows.append({"EmployeeId": mid, "EmploymentEnd": eind})
    return rows


def gen_profit_employees_basic(r):
    return [{"EmployeeId": mid, "DvId": ("ACTIEF" if r.random() > 0.15 else "UIT")}
            for mid in _emp_ids(N_MED)]


def gen_profit_illness(r):
    meds = _emp_ids(N_MED)
    return [{"AbsenceId": f"A{idx:05d}", "EmployeeId": r.choice(meds),
             "RecoveredCode": ("OPEN" if r.random() > 0.7 else "HERSTELD")}
            for idx in range(1, 81)]


def gen_profit_timetable(r):
    rows = []
    for mid in _emp_ids(N_MED):
        actief = r.random() > 0.12
        rows.append({"EmployeeId": mid,
                     "EndDate": "" if actief else f"2025-{r.randint(1,12):02d}-01",
                     "HoursPerWeek": round(r.uniform(16, 36), 1)})
    return rows


# -- Datasetregister ----------------------------------------------------------
DATASETS = [
    DatasetDef("client_ons.csv", ONZ_ZORG + "Client", "objectId", {
        "objectId": _S(ONZ_G + "identificatie"),
        "wlzProfiel": _S(ONZ_ZORG + "wlzProfiel"),
    }, gen_client_ons),
    DatasetDef("medewerker_ons.csv", ONZ_PERS + "Medewerker", "identificationNo", {
        "identificationNo": _S(ONZ_PERS + "identificatie"),
    }, gen_medewerker_ons),
    DatasetDef("medewerker_afas_hrm.csv", ONZ_PERS + "Medewerker", "PersoneelsNummer", {
        "PersoneelsNummer": _S(ONZ_PERS + "personeelsnummer"),
    }, gen_medewerker_afas),
    DatasetDef("vestiging_ons.csv", ONZ_ORG + "Vestiging", "objectId", {
        "objectId": _S(ONZ_G + "identificatie"),
        "regio": _S(ONZ_ORG + "regio"),
    }, gen_vestiging_ons),
    DatasetDef("functie_ons.csv", ONZ_PERS + "Functie", None, {
        "functie": _S(ONZ_PERS + "functienaam"),
    }, gen_functie_ons),
    DatasetDef("financieleboeking_afas_fin.csv", ONZ_FIN + "Boeking", None, {
        "grootBoekRekening": _S(ONZ_FIN + "grootboekrekening"),
        "boekingsBedrag": _S(ONZ_FIN + "bedrag", datatype="decimal"),
    }, gen_financieel),
    DatasetDef("grootboekrubriek_afas_fin.csv", ONZ_FIN + "Grootboekrekening", "grootboekRekeningNummer", {
        "grootboekRekeningNummer": _S(ONZ_FIN + "rekeningnummer"),
    }, gen_grootboekrubriek),
    DatasetDef("wlzkostenplaats_afas_fin.csv", ONZ_FIN + "Kostenplaats", "kostenPlaats", {
        "kostenPlaats": _S(ONZ_FIN + "kostenplaats"),
    }, gen_kostenplaats),
    DatasetDef("verzuim_ons.csv", ONZ_PERS + "Verzuim", None, {
        "employeeId": _S(ONZ_PERS + "medewerkerref"),
    }, gen_verzuim_ons),
    DatasetDef("verzuim_afas_hrm.csv", ONZ_PERS + "VerzuimAfas", None, {
        "PersoneelsNummer": _S(ONZ_PERS + "personeelsnummer"),
    }, gen_verzuim_afas),
    DatasetDef("werkovereenkomst_afas_hrm.csv", ONZ_PERS + "WerkovereenkomstAfas", "DienstverbandNummer", {
        "DienstverbandNummer": _S(ONZ_PERS + "dienstverbandnummer"),
        "PersoneelsNummer": _S(ONZ_PERS + "personeelsnummer"),
    }, gen_werkovereenkomst_afas),
    DatasetDef("werkovereenkomst_ons.csv", ONZ_PERS + "Werkovereenkomst", "objectId", {
        "objectId": _S(ONZ_G + "identificatie"),
        "employeeId": _S(ONZ_PERS + "medewerkerref"),
    }, gen_werkovereenkomst_ons),
    DatasetDef("Profit_Employees_150_voorbeeld.xml", ONZ_PERS + "Dienstverband", "EmployeeId", {
        "EmployeeId": _S(ONZ_PERS + "medewerkerref"),
        "EmploymentEnd": _S(ONZ_PERS + "einddatum", datatype="date"),
    }, gen_profit_employees),
    DatasetDef("Profit_Employees_basic_150_voorbeeld.xml", ONZ_PERS + "DienstverbandBasic", "EmployeeId", {
        "EmployeeId": _S(ONZ_PERS + "medewerkerref"),
        "DvId": _S(ONZ_PERS + "dienstverbandstatus"),
    }, gen_profit_employees_basic),
    DatasetDef("Profit_Illness_150_voorbeeld.xml", ONZ_PERS + "Verzuimmelding", "AbsenceId", {
        "AbsenceId": _S(ONZ_PERS + "verzuimid"),
        "EmployeeId": _S(ONZ_PERS + "medewerkerref"),
        "RecoveredCode": _S(ONZ_PERS + "herstelcode"),
    }, gen_profit_illness),
    DatasetDef("Profit_Timetable_150_voorbeeld.xml", ONZ_PERS + "Rooster", "EmployeeId", {
        "EmployeeId": _S(ONZ_PERS + "medewerkerref"),
        "EndDate": _S(ONZ_PERS + "roostereinddatum", datatype="date"),
        "HoursPerWeek": _S(ONZ_PERS + "urenperweek", datatype="decimal"),
    }, gen_profit_timetable),
]

_BY_NAME = {d.naam: d for d in DATASETS}
SEED = 20260612


def genereer_alles() -> dict:
    out = {}
    for i, d in enumerate(DATASETS):
        out[d.naam] = d.generate(random.Random(SEED + i))
    return out


# -- SPARQL-afleiding ---------------------------------------------------------
_PREFIXES = (
    f"PREFIX onz-g: <{ONZ_G}>\n"
    f"PREFIX onz-pers: <{ONZ_PERS}>\n"
    f"PREFIX onz-org: <{ONZ_ORG}>\n"
    f"PREFIX onz-fin: <{ONZ_FIN}>\n"
    f"PREFIX onz-zorg: <{ONZ_ZORG}>\n"
)


def _concept(ds, veld):
    cfg = ds.mapping.get(veld)
    return cfg["concept_uri"] if cfg else None


def sparql_for_rule(rule: dict):
    ds = _BY_NAME.get(rule.get("source_dataset"))
    if not ds:
        return None
    agg = rule.get("aggregation", {})
    fn = (agg.get("function") or "").lower()
    veld = agg.get("field")
    concept = _concept(ds, veld)
    if not concept:
        return None
    patterns = [f"?s a <{ds.class_uri}> .", f"?s <{concept}> ?v ."]
    filters = []
    for flt in rule.get("filters", []):
        fveld = flt.get("field")
        fconcept = _concept(ds, fveld)
        op = (flt.get("operator") or "").lower()
        if not fconcept:
            continue
        if op == "isnull":
            filters.append(f"FILTER NOT EXISTS {{ ?s <{fconcept}> ?nx }}")
        elif op == "eq":
            _val = flt.get("value")
            patterns.append(f"?s <{fconcept}> ?f_{fveld} .")
            filters.append(f'FILTER( STR(?f_{fveld}) = "{_val}" )')
    if fn == "count":
        select = "(COUNT(?v) AS ?n)"
    elif fn == "nunique":
        select = "(COUNT(DISTINCT ?v) AS ?n)"
    elif fn == "sum":
        select = "(SUM(?v) AS ?n)"
    elif fn == "mean":
        select = "(AVG(?v) AS ?n)"
    else:
        return None
    body = "\n    ".join(patterns + filters)
    return f"{_PREFIXES}SELECT {select} WHERE {{\n    {body}\n}}"


# -- Validatie-referentie -----------------------------------------------------
def _is_leeg(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def referentie_for_rule(rule: dict, records: list):
    agg = rule.get("aggregation", {})
    fn = (agg.get("function") or "").lower()
    veld = agg.get("field")
    rows = records
    for flt in rule.get("filters", []):
        f, op, val = flt.get("field"), (flt.get("operator") or "").lower(), flt.get("value")
        if op == "isnull":
            rows = [x for x in rows if _is_leeg(x.get(f))]
        elif op == "eq":
            rows = [x for x in rows if str(x.get(f)) == str(val)]
    vals = [x.get(veld) for x in rows if not _is_leeg(x.get(veld))]
    if fn == "count":
        return float(len(vals))
    if fn == "nunique":
        return float(len(set(vals)))
    if fn == "sum":
        return round(float(sum(float(v) for v in vals)), 2)
    if fn == "mean":
        return round(float(sum(float(v) for v in vals) / len(vals)), 2) if vals else None
    return None
