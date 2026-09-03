"""
salary_provider package
========================
Split from the former `salary_provider.py` module (200-line refactor).

Sibling files:
- constants.py    Month-name lookup, AI row cap, chronological sort key.
- aggregation.py  Phase functions for ORM aggregation: totals, company
                   breakdown, yearly summary + YoY growth.
- timeline.py      Phase functions for chronological entry analysis, the
                   AI-facing capped timeline, and the single latest entry.
- provider.py      SalaryDataProvider class — orchestrates the phases above
                   and assembles the final response dict.

Update this docstring whenever a sibling file is added, removed, or its
responsibility changes.
"""

from __future__ import annotations

from core.services.ai.providers.salary_provider.provider import SalaryDataProvider

__all__ = ["SalaryDataProvider"]
