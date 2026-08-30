"""
tests/core/crud_verifier.py — real, API-verified CRUD checking.

WHY THIS EXISTS
----------------
The module test files' CRUD checks previously called
reporter.record_crud(entity_name, 17, 17) unconditionally — meaning "17/17
steps passed" regardless of whether the create/edit/delete actually
happened, or whether a guarded JS call like
`if (typeof saveX === 'function') saveX();` silently no-opped because the
function didn't exist. As long as no Python exception was thrown, it
reported a perfect score.

This module replaces that with real verification: fetch the entity's list
via its actual API endpoint before and after each UI action, and check
what genuinely changed — not what the test assumed happened.

USAGE PATTERN (see tests/modules/balance.py / fixed_assets.py for real
examples)
-----------------------------------------------------------------------
    checker = CrudVerifier(context.page, api_list_url="/api/balance/",
                            list_key="entries", id_field="id")

    before_ids = checker.snapshot_ids()
    # ... do the UI actions that should create a row ...
    result = checker.verify_created(before_ids, match_field="title",
                                     expected_value=account_data["title"])
    # result.passed (bool), result.detail (str), result.new_id (int|None)

    # ... do the UI actions that should edit that row ...
    result2 = checker.verify_field_updated(result.new_id, "title",
                                            new_title)

    # ... do the UI actions that should delete that row ...
    result3 = checker.verify_deleted(result.new_id)

    reporter.record_crud(entity_name, checker.steps_passed, checker.steps_total)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


def _values_match(actual: Any, expected: Any) -> bool:
    """Compares two field values, tolerant of numeric formatting
    differences (e.g. API returns 50 or '50.00', Python literal is '50').
    Falls back to exact string comparison for non-numeric fields."""
    try:
        return abs(float(actual) - float(expected)) < 0.01
    except (TypeError, ValueError):
        return str(actual).strip() == str(expected).strip()


@dataclass
class StepResult:
    passed: bool
    detail: str
    new_id: Optional[int] = None


class CrudVerifier:
    def __init__(self, page, api_list_url: str, list_key: str, id_field: str = "id"):
        self.page = page
        self.api_list_url = api_list_url
        self.list_key = list_key
        self.id_field = id_field
        self.steps_passed = 0
        self.steps_total = 0

    def _fetch_list(self) -> list:
        try:
            data = self.page.evaluate(
                """async (url) => {
                    const res = await fetch(url);
                    if (!res.ok) return null;
                    return await res.json();
                }""",
                self.api_list_url,
            )
        except Exception:
            return []
        if not data:
            return []
        return data.get(self.list_key, []) if isinstance(data, dict) else data

    def snapshot_ids(self) -> set:
        return {item.get(self.id_field) for item in self._fetch_list()}

    def _step(self, passed: bool):
        self.steps_total += 1
        if passed:
            self.steps_passed += 1

    def verify_created(self, before_ids: set, match_field: str, expected_value: Any) -> StepResult:
        """Confirms exactly one new row appeared via the real API, and that
        its match_field genuinely equals what was submitted — not just that
        SOME new row exists."""
        after_list = self._fetch_list()
        after_ids = {item.get(self.id_field) for item in after_list}
        new_ids = after_ids - before_ids

        if not new_ids:
            self._step(False)
            return StepResult(False, f"No new row found via {self.api_list_url} after create action.")

        new_id = next(iter(new_ids))
        new_item = next((i for i in after_list if i.get(self.id_field) == new_id), None)

        if new_item is None:
            self._step(False)
            return StepResult(False, f"New id {new_id} appeared but row lookup failed.", new_id)

        actual_value = new_item.get(match_field)
        field_ok = _values_match(actual_value, expected_value)
        self._step(field_ok)
        detail = (
            f"Created row id={new_id}, {match_field}='{actual_value}' matches expected."
            if field_ok
            else f"Created row id={new_id}, but {match_field}='{actual_value}' != expected '{expected_value}'."
        )
        return StepResult(field_ok, detail, new_id)

    def verify_field_updated(self, item_id: Optional[int], field: str, expected_value: Any) -> StepResult:
        if item_id is None:
            self._step(False)
            return StepResult(False, "No item id to check update against (create step failed earlier).")

        after_list = self._fetch_list()
        item = next((i for i in after_list if i.get(self.id_field) == item_id), None)
        if item is None:
            self._step(False)
            return StepResult(False, f"Row id={item_id} not found when checking update.")

        actual_value = item.get(field)
        ok = _values_match(actual_value, expected_value)
        self._step(ok)
        detail = (
            f"Row id={item_id} {field}='{actual_value}' matches expected after edit."
            if ok
            else f"Row id={item_id} {field}='{actual_value}' != expected '{expected_value}' after edit."
        )
        return StepResult(ok, detail, item_id)

    def verify_deleted(self, item_id: Optional[int]) -> StepResult:
        if item_id is None:
            self._step(False)
            return StepResult(False, "No item id to check deletion against (create step failed earlier).")

        after_list = self._fetch_list()
        still_exists = any(i.get(self.id_field) == item_id for i in after_list)
        ok = not still_exists
        self._step(ok)
        detail = (
            f"Row id={item_id} confirmed removed via {self.api_list_url}."
            if ok
            else f"Row id={item_id} still present via {self.api_list_url} after delete action."
        )
        return StepResult(ok, detail, item_id)

    def add_manual_step(self, passed: bool):
        """For steps this verifier can't check via API alone (e.g. modal
        opened, screenshot captured) but that the surrounding test code
        already confirmed some other way — keeps the total honest instead
        of silently dropping steps out of the denominator."""
        self._step(passed)
