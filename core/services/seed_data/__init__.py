"""
seed_data support package
===========================
Static seed-data constants used by the `seed_data` management command
(kept out of management/commands/ so that command stays a flat,
Django-discoverable module; Django's management-command auto-discovery
(pkgutil.iter_modules with `not is_pkg`) only recognizes flat modules
there, not packages).

Sibling files:
- fixtures.py   COMPANIES, SALARY_DATA, CURRENCIES, BANKS, BALANCE_DATA,
                SETTINGS_DATA
"""

from core.services.seed_data.fixtures import (
    BALANCE_DATA,
    BANKS,
    COMPANIES,
    CURRENCIES,
    SALARY_DATA,
    SETTINGS_DATA,
)

__all__ = [
    "COMPANIES",
    "SALARY_DATA",
    "CURRENCIES",
    "BANKS",
    "BALANCE_DATA",
    "SETTINGS_DATA",
]
