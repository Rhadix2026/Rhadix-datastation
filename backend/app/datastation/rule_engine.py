"""
Rhadix Reconciliation Engine — Rule Engine
Laadt en valideert YAML/JSON indicatordefinities.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, validator


class FilterCondition(BaseModel):
    field: str
    operator: str          # eq, ne, gt, gte, lt, lte, in, not_in, notnull, isnull
    value: Any = None


class AggregationConfig(BaseModel):
    function: str          # count, sum, mean, median, nunique
    field: str | None = None


class ToleranceConfig(BaseModel):
    absolute: float = 0.0
    percentage: float = 0.0


class IndicatorRule(BaseModel):
    indicator_id: str
    name: str
    description: str = ""
    source_dataset: str
    peildatum_field: str | None = None
    peildatum: str | None = None
    dayfirst: bool = False          # True voor Nederlandse datumnotatie dd/MM/yyyy
    filters: list[FilterCondition] = Field(default_factory=list)
    aggregation: AggregationConfig
    sparql_query: str | None = None
    sparql_endpoint: str | None = None
    tolerance: ToleranceConfig = Field(default_factory=ToleranceConfig)
    tags: list[str] = Field(default_factory=list)

    @validator("indicator_id")
    def _no_spaces(cls, v: str) -> str:
        if " " in v:
            raise ValueError("indicator_id mag geen spaties bevatten")
        return v


class RuleEngine:
    def __init__(self) -> None:
        self._rules: dict[str, IndicatorRule] = {}

    def load_file(self, path: str | Path) -> None:
        path = Path(path)
        text = path.read_text(encoding="utf-8")
        if path.suffix in {".yaml", ".yml"}:
            data = yaml.safe_load(text)
        elif path.suffix == ".json":
            data = json.loads(text)
        else:
            raise ValueError(f"Onbekend bestandstype: {path.suffix}")
        if isinstance(data, dict) and "indicator_id" in data:
            data = [data]
        for item in data:
            rule = IndicatorRule(**item)
            self._rules[rule.indicator_id] = rule

    def load_directory(self, directory: str | Path) -> None:
        directory = Path(directory)
        for f in sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml")) + sorted(directory.glob("*.json")):
            self.load_file(f)

    def get(self, indicator_id: str) -> IndicatorRule:
        if indicator_id not in self._rules:
            raise KeyError(f"Indicator niet gevonden: {indicator_id}")
        return self._rules[indicator_id]

    def list_rules(self) -> list[IndicatorRule]:
        return list(self._rules.values())

    def to_dict(self) -> list[dict]:
        return [r.dict() for r in self._rules.values()]
