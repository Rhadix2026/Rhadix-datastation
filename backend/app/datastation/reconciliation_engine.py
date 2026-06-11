"""
Rhadix Reconciliation Engine — Reconciliation & Difference Analyzer
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd
import requests

from .calculation_engine import CalcResult
from .rule_engine import IndicatorRule, ToleranceConfig


class ReconciliationStatus(str, Enum):
    OK = "OK"
    WARNING = "Warning"
    ERROR = "Error"
    UNKNOWN = "Unknown"


def _status_from_score(score: float) -> str:
    if score >= 100: return "Excellent"
    if score >= 95:  return "Minor deviation"
    if score >= 80:  return "Attention required"
    return "Insufficient"


class SPARQLEngine:
    def __init__(self, default_endpoint: str | None = None) -> None:
        self.default_endpoint = default_endpoint

    def execute(self, query: str, endpoint: str | None = None) -> float | None:
        url = endpoint or self.default_endpoint
        if not url:
            raise ValueError("Geen SPARQL-endpoint geconfigureerd.")
        resp = requests.post(url, data={"query": query},
                             headers={"Accept": "application/sparql-results+json"}, timeout=30)
        resp.raise_for_status()
        bindings = resp.json().get("results", {}).get("bindings", [])
        if not bindings:
            return None
        for _, val in bindings[0].items():
            try:
                return float(val["value"])
            except (KeyError, ValueError):
                continue
        return None


@dataclass
class ReconciliationResult:
    indicator_id: str
    indicator_name: str
    expected_value: float | None
    actual_value: float | None
    absolute_difference: float | None
    percentage_difference: float | None
    status: ReconciliationStatus
    confidence_score: float
    reconciliation_score_label: str
    drill_down: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "indicator_id": self.indicator_id,
            "indicator_name": self.indicator_name,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "absolute_difference": self.absolute_difference,
            "percentage_difference": self.percentage_difference,
            "status": self.status.value,
            "confidence_score": self.confidence_score,
            "reconciliation_score_label": self.reconciliation_score_label,
            "drill_down": self.drill_down,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


class ReconciliationEngine:
    def __init__(self, sparql_engine: SPARQLEngine | None = None) -> None:
        self.sparql_engine = sparql_engine or SPARQLEngine()

    def reconcile(self, rule: IndicatorRule, calc_result: CalcResult,
                  actual_value: float | None = None,
                  sparql_query_override: str | None = None,
                  sparql_endpoint_override: str | None = None) -> ReconciliationResult:
        if actual_value is None:
            actual_value = self._fetch_actual(
                rule,
                sparql_query_override=sparql_query_override,
                sparql_endpoint_override=sparql_endpoint_override,
            )

        abs_diff, pct_diff, status, confidence = self._compare(
            calc_result.expected_value, actual_value, rule.tolerance)
        drill_down = DifferenceAnalyzer.analyze(
            calc_result.included_records, calc_result.excluded_records, rule)

        return ReconciliationResult(
            indicator_id=rule.indicator_id,
            indicator_name=rule.name,
            expected_value=calc_result.expected_value,
            actual_value=actual_value,
            absolute_difference=abs_diff,
            percentage_difference=pct_diff,
            status=status,
            confidence_score=confidence,
            reconciliation_score_label=_status_from_score(confidence),
            drill_down=drill_down,
            metadata={"record_count": calc_result.record_count,
                      "peildatum": rule.peildatum,
                      "tolerance": rule.tolerance.dict(),
                      **calc_result.metadata},
        )

    def _fetch_actual(self, rule, sparql_query_override: str | None = None,
                       sparql_endpoint_override: str | None = None):
        query = sparql_query_override or rule.sparql_query
        if not query:
            return None
        endpoint = sparql_endpoint_override or rule.sparql_endpoint
        if not endpoint:
            return None  # geen endpoint → geen fout, status wordt Unknown
        return self.sparql_engine.execute(query, endpoint=endpoint)

    @staticmethod
    def _compare(expected, actual, tolerance):
        if expected is None or actual is None:
            return None, None, ReconciliationStatus.UNKNOWN, 0.0
        abs_diff = abs(expected - actual)
        pct_diff = (abs_diff / expected * 100) if expected != 0 else (0.0 if actual == 0 else 100.0)
        within_abs = abs_diff <= tolerance.absolute
        within_pct = pct_diff <= tolerance.percentage
        if within_abs or within_pct:
            status, confidence = ReconciliationStatus.OK, max(0.0, 100.0 - pct_diff)
        elif pct_diff <= tolerance.percentage * 2:
            status, confidence = ReconciliationStatus.WARNING, max(0.0, 100.0 - pct_diff * 1.5)
        else:
            status, confidence = ReconciliationStatus.ERROR, max(0.0, 100.0 - pct_diff * 2)
        return round(abs_diff, 4), round(pct_diff, 4), status, round(min(confidence, 100.0), 2)


class DifferenceAnalyzer:
    @staticmethod
    def analyze(included_records, excluded_records, rule):
        issues = []
        for rec in excluded_records:
            issues.append({"category": DifferenceAnalyzer._classify(rec, rule),
                           "source": "brondata", "record": _safe_record(rec)})
        for rec in included_records:
            bad = DifferenceAnalyzer._check_invalid_codes(rec)
            if bad:
                issues.append({"category": "invalid_codes", "source": "brondata",
                               "record": _safe_record(rec), "invalid_fields": bad})
        return issues

    @staticmethod
    def _classify(rec, rule):
        if rule.peildatum_field and rule.peildatum_field in rec:
            val = rec[rule.peildatum_field]
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return "wrong_dates"
            try:
                if rule.peildatum and pd.Timestamp(val) < pd.Timestamp(rule.peildatum):
                    return "wrong_dates"
            except Exception:
                return "wrong_dates"
        nullable = [f.field for f in rule.filters if f.operator == "notnull"]
        for fld in nullable:
            if fld in rec and (rec[fld] is None or (isinstance(rec[fld], float) and pd.isna(rec[fld]))):
                return "missing_relationships"
        return "missing_in_rdf"

    @staticmethod
    def _check_invalid_codes(rec):
        bad = []
        for k, v in rec.items():
            if any(kw in k.lower() for kw in ("code", "type", "status", "id")):
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    bad.append(k)
        return bad


@dataclass
class BatchReconciliationResult:
    results: list[ReconciliationResult]

    @property
    def reconciliation_score(self) -> float:
        if not self.results: return 0.0
        correct = sum(1 for r in self.results if r.status == ReconciliationStatus.OK)
        return round(correct / len(self.results) * 100, 2)

    @property
    def score_label(self) -> str:
        return _status_from_score(self.reconciliation_score)

    def to_dict(self) -> dict:
        return {"reconciliation_score": self.reconciliation_score,
                "score_label": self.score_label,
                "total_indicators": len(self.results),
                "results": [r.to_dict() for r in self.results]}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


def _safe_record(rec, max_fields=15):
    items = list(rec.items())[:max_fields]
    return {k: (None if (isinstance(v, float) and pd.isna(v)) else v) for k, v in items}
