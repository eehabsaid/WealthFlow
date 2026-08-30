"""Shared atomic scenario creation for ScenarioPlannerService.

NOTE (200-line file convention): extracted from the original monolithic
core/services/financial_advisor/scenario_planner_service.py (716 lines).
See __init__.py for the full package layout.
"""
from __future__ import annotations

from typing import List

from django.db import transaction

from core.models import Scenario, ScenarioEvent


def create_scenario_record(
    name: str,
    description: str = "",
    is_baseline_pinned: bool = False,
    events: List[dict] | None = None,
) -> Scenario:
    """
    Shared atomic scenario creation function.
    Validates name and events, creating Scenario and ScenarioEvents inside transaction.atomic().
    Raises ValueError if validation fails.
    """
    clean_name = str(name or "").strip()
    if not clean_name:
        raise ValueError("Name is required")

    events_list = events or []
    if not isinstance(events_list, list):
        raise ValueError("Events must be a list")

    for idx, ev_data in enumerate(events_list):
        if not isinstance(ev_data, dict):
            raise ValueError(f"Event at index {idx} must be an object")
        etype = str(ev_data.get("event_type", "")).strip()
        edate = ev_data.get("event_date")
        if not etype or not edate:
            raise ValueError(f"event_type and event_date are required for event at index {idx}")

    with transaction.atomic():
        sc = Scenario.objects.create(
            name=clean_name,
            description=str(description or "").strip(),
            is_baseline_pinned=bool(is_baseline_pinned),
        )
        for idx, ev_data in enumerate(events_list):
            etype = str(ev_data.get("event_type", "")).strip()
            edate = ev_data.get("event_date")
            ScenarioEvent.objects.create(
                scenario=sc,
                event_type=etype,
                event_date=edate,
                params=ev_data.get("params", {}) if isinstance(ev_data.get("params"), dict) else {},
                order=int(ev_data.get("order", idx)),
            )
        return sc
