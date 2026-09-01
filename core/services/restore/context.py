"""
NOTE: Part of the restore package split (see __init__.py docstring for the
200-line-per-file convention this package follows).

context.py: typed dataclass carriers passed between the restore command's
phase functions, mirroring the project's mixin/phase dataclass-carrier
convention (e.g. PortfolioContext, ReportContext).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RestoreRunContext:
    """Per-run options plus the Command's stdout/style, so phase functions
    can write progress output without needing the full Command instance."""

    stdout: Any
    style: Any
    dry_run: bool
    tables_filter: set[str]
    skip_users: bool
    overwrite: bool


@dataclass
class RestoreTotals:
    """Running tally accumulated across all restored tables."""

    created: int = 0
    updated: int = 0
    skipped: int = 0
    tables_restored: int = 0
    disconnected_signals: list = field(default_factory=list)
