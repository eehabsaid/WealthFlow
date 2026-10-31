"""A figure the model calculated itself (a difference, a sum, a percentage change, a share, a what-if total) is accepted when code can redo the
arithmetic from OTHER figures of the same answer that are themselves proven (found in a tool result or computed by code). Only the answer's own
supported figures are operands (a handful, so a lucky coincidence is very unlikely); every other figure must still be in a tool result."""

from __future__ import annotations

import re
from decimal import Decimal
from itertools import permutations

MAX_OPERANDS = 24


def _tolerance(printed: str) -> Decimal:
    """Half a unit of the last printed digit (36.1 may stand for 36.09..36.15); whole numbers must be exact."""
    m = re.search(r"[.,](\d{1,2})\s*%?$", str(printed).strip())
    return Decimal("0.5") * Decimal(10) ** -(len(m.group(1)) if m else 0) + Decimal("0.0001")


def _results(a: Decimal, b: Decimal):
    yield a + b
    yield a - b
    yield abs(a - b)
    if b:
        yield a / b * 100            # share
        yield (a - b) / b * 100      # change in percent
        yield abs(a - b) / b * 100
    if 0 < abs(b) <= 100:            # a what-if: b percent of a, or a lowered / raised by b percent
        yield a * b / 100
        yield a * (100 - b) / 100
        yield a * (100 + b) / 100


def derivable(printed: str, readings: set, operands: set) -> bool:
    ops = sorted(operands, key=abs, reverse=True)[:MAX_OPERANDS]
    tol = _tolerance(printed)
    return any(abs(r - target) <= tol for a, b in permutations(ops, 2) for target in _results(a, b) for r in readings)
