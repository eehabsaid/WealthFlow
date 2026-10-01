"""Typed contracts of the query engine: a declared Capability, a QueryRequest (the typed,
read-only, owner-scoped question) and a QueryResult (what an executor computed).

Executors never see raw text and renderers never see the database: the request is the only
thing that crosses from language understanding to data access.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class Metric:
    name: str
    terms: tuple[str, ...] = ()          # regexes on normalized text (en + ar); empty = default only


@dataclass(frozen=True)
class Capability:
    """Declared once by a data provider (BaseContextProvider.get_query_capabilities)."""

    key: str
    provider_key: str
    label: str
    terms: tuple[tuple[str, int], ...]           # (regex, weight): evidence the question is about this
    metrics: tuple[Metric, ...]
    default_metric: str
    executor: Callable[[Any, "QueryRequest"], "QueryResult"]
    dimensions: tuple[tuple[str, tuple[str, ...]], ...] = ()   # group_by name -> phrase regexes
    filters: tuple[str, ...] = ()                # currency | karat | side | category | bank | asset_type
    time: str = "none"                           # required | optional | none
    sources: tuple[str, ...] = ()
    follow_subject: str = ""                    # words appended to a short follow-up ("and how much I hold?") after this capability
    latest_metrics: tuple[str, ...] = ()        # metrics that make sense with no period ("last expense")

    def metric_names(self) -> list[str]:
        return [m.name for m in self.metrics]

    def dimension_names(self) -> list[str]:
        return [d[0] for d in self.dimensions]


@dataclass
class QueryRequest:
    capability: str
    metric: str = ""
    group_by: str = ""
    periods: list[tuple[int, int]] = field(default_factory=list)   # (year, month), ascending
    latest: bool = False
    n: int | None = None
    filters: dict[str, Any] = field(default_factory=dict)
    lang: str = "en"

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability, "metric": self.metric, "group_by": self.group_by,
            "periods": [f"{y}-{m:02d}" for y, m in self.periods], "latest": self.latest,
            "n": self.n, "filters": self.filters, "lang": self.lang,
        }


@dataclass
class Row:
    cells: list[str]
    bold: bool = False


@dataclass
class QueryResult:
    """Fully computed answer. `facts` carries machine values for the narrative path."""

    intro: str = ""
    columns: list[str] = field(default_factory=list)
    rows: list[Row] = field(default_factory=list)
    footer: str = ""
    facts: dict[str, Any] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)
