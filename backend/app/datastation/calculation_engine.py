"""
Rhadix Reconciliation Engine — Calculation Engine
Laadt brondata, past filters toe en berekent de verwachte indicatorwaarde.
Ondersteunde formaten: CSV, Excel (.xlsx/.xls), AFAS XML (Profit GET-connector)
"""

from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .rule_engine import AggregationConfig, FilterCondition, IndicatorRule


@dataclass
class CalcResult:
    indicator_id: str
    expected_value: float | int | None
    record_count: int
    included_records: list[dict]
    excluded_records: list[dict]
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# XML-parser voor AFAS Profit GET-connector output
# Structuur: <RootElement><RecordElement><Veld>waarde</Veld>...</RecordElement>...
# ---------------------------------------------------------------------------

_AFAS_DATE_COMPACT = re.compile(r"^\d{8}$")          # 20200303
_AFAS_DATETIME_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T")  # 2026-04-19T00:00:00


def _records_container(root: "ET.Element") -> "ET.Element":
    """Bepaal het element dat de herhaalde record-elementen bevat.

    Twee AFAS-exportvarianten:
      • named export   : <Profit_Employees><Employee>…  → records staan onder root
      • GET-connector  : <root><skip/><take/><rows><row>… → records onder <rows>
    """
    rows_el = root.find("rows")
    if rows_el is not None and len(list(rows_el)) > 0:
        return rows_el
    return root


def _parse_afas_xml(source: io.BytesIO) -> pd.DataFrame:
    """Parseer AFAS Profit XML naar een pandas DataFrame.

    Ondersteunt zowel het named-export-formaat (<Profit_Employees><Employee>)
    als het GET-connector-formaat (<root><rows><row>). Lege elementen — ook
    die met attribuut nil="true" — worden None. Datumvelden worden herkend.
    """
    source.seek(0)
    tree = ET.parse(source)
    root = tree.getroot()
    container = _records_container(root)

    rows = []
    for record in container:        # record-elementen (Employee / row)
        row: dict = {}
        for field_el in record:     # children van record = velden
            tag = field_el.tag
            text = field_el.text
            is_nil = (field_el.get("nil") or "").lower() == "true"
            if is_nil or text is None or text.strip() == "":
                row[tag] = None
            elif _AFAS_DATE_COMPACT.match(text.strip()):
                try:
                    row[tag] = pd.to_datetime(text.strip(), format="%Y%m%d")
                except Exception:
                    row[tag] = text.strip()
            elif _AFAS_DATETIME_ISO.match(text.strip()):
                try:
                    row[tag] = pd.to_datetime(text.strip())
                except Exception:
                    row[tag] = text.strip()
            else:
                row[tag] = text.strip()
        if row:
            rows.append(row)

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def _is_xml(source: io.BytesIO) -> bool:
    """Controleer of de bron XML is door de eerste bytes te lezen."""
    source.seek(0)
    header = source.read(64).lstrip()
    source.seek(0)
    return header.startswith(b"<?xml") or header.startswith(b"<")


class DataLoader:
    @staticmethod
    def load(source, **read_kwargs) -> pd.DataFrame:
        if isinstance(source, (str, Path)):
            path = Path(source)
            if path.suffix in {".xlsx", ".xls"}:
                return pd.read_excel(path, **read_kwargs)
            if path.suffix == ".xml":
                with open(path, "rb") as f:
                    return _parse_afas_xml(io.BytesIO(f.read()))
            return pd.read_csv(path, **read_kwargs)
        if isinstance(source, bytes):
            source = io.BytesIO(source)
        # Auto-detectie op basis van inhoud
        if _is_xml(source):
            return _parse_afas_xml(source)
        try:
            source.seek(0)
            return pd.read_csv(source, **read_kwargs)
        except Exception:
            source.seek(0)
            return pd.read_excel(source, **read_kwargs)


def _apply_filter(df: pd.DataFrame, condition: FilterCondition) -> pd.Series:
    col = df[condition.field]
    op = condition.operator
    val = condition.value
    if op == "eq":      return col == val
    if op == "ne":      return col != val
    if op == "gt":      return col > val
    if op == "gte":     return col >= val
    if op == "lt":      return col < val
    if op == "lte":     return col <= val
    if op == "in":      return col.isin(val)
    if op == "not_in":  return ~col.isin(val)
    if op == "notnull": return col.notna()
    if op == "isnull":  return col.isna()
    raise ValueError(f"Onbekende operator: {op}")


class CalculationEngine:
    def __init__(self, data_dir=None) -> None:
        self.data_dir = Path(data_dir) if data_dir else None

    def calculate(self, rule: IndicatorRule, source=None) -> CalcResult:
        df = self._load_data(rule, source)
        df_included, df_excluded = self._apply_filters(df, rule)
        expected_value = self._aggregate(df_included, rule.aggregation)
        return CalcResult(
            indicator_id=rule.indicator_id,
            expected_value=expected_value,
            record_count=len(df_included),
            included_records=df_included.to_dict(orient="records"),
            excluded_records=df_excluded.to_dict(orient="records"),
            metadata={"total_rows": len(df), "peildatum": rule.peildatum, "source_dataset": rule.source_dataset},
        )

    def _load_data(self, rule, source):
        if source is None:
            if self.data_dir is None:
                raise ValueError("Geen data_dir ingesteld en geen source opgegeven.")
            source = self.data_dir / rule.source_dataset
        return DataLoader.load(source)

    def _apply_filters(self, df, rule):
        mask = pd.Series([True] * len(df), index=df.index)
        for condition in rule.filters:
            if condition.field not in df.columns:
                continue
            mask &= _apply_filter(df, condition)
        if rule.peildatum and rule.peildatum_field and rule.peildatum_field in df.columns:
            df[rule.peildatum_field] = pd.to_datetime(
                df[rule.peildatum_field], errors="coerce", dayfirst=getattr(rule, "dayfirst", False)
            )
            cutoff = pd.Timestamp(rule.peildatum)
            mask &= (df[rule.peildatum_field].isna()) | (df[rule.peildatum_field] >= cutoff)
        return df[mask].copy(), df[~mask].copy()

    @staticmethod
    def _aggregate(df, agg: AggregationConfig):
        if df.empty:
            return 0
        fn, col = agg.function, agg.field
        if fn == "count":   return int(len(df) if col is None else df[col].count() if col in df.columns else 0)
        if col is None:     raise ValueError(f"Aggregatiefunctie '{fn}' vereist een 'field'.")
        if col not in df.columns:
            return None  # kolom ontbreekt in bronbestand — geen fout, wel Unknown status
        # Voor numerieke functies: converteer kolom naar numeriek (vangt XML-stringwaarden op)
        if fn in ("sum", "mean", "median"):
            series = pd.to_numeric(df[col], errors="coerce")
        else:
            series = df[col]
        if fn == "sum":     return float(series.sum())
        if fn == "mean":    v = series.mean();    return round(float(v), 4) if not pd.isna(v) else None
        if fn == "median":  v = series.median();  return round(float(v), 4) if not pd.isna(v) else None
        if fn == "nunique": return int(series.nunique())
        raise ValueError(f"Onbekende aggregatiefunctie: {fn}")
