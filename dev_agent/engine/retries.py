"""The 3-attempt rule: after a failure, the agent gets at most 3 failed fix attempts on the SAME underlying error, then it must stop and report.
A different error starts a new count; a passing check resets everything."""

from __future__ import annotations

import re

LIMIT = 3
_ERROR = re.compile(r"error|fail|traceback|exception|assert", re.I)


def signature(text: str) -> str:
    """A stable fingerprint of an error: the first error-like line with numbers, hex ids and paths blanked out."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    line = next((l for l in lines if _ERROR.search(l)), lines[-1] if lines else "unknown error")
    line = re.sub(r"[A-Za-z]:[\\/][^\s:'\"]*|(?:/[\w.\-]+){2,}", "<path>", line)
    line = re.sub(r"0x[0-9a-f]+|\b\d+\b", "#", line.lower())
    return re.sub(r"\s+", " ", line)[:160]


class RetryTracker:
    def __init__(self, limit: int = LIMIT):
        self.limit, self.last, self.failed_fixes = limit, None, 0

    def failure(self, sig: str) -> bool:
        """Record a failing check. True means: stop, 3 fix attempts did not remove this error."""
        if sig == self.last:
            self.failed_fixes += 1
        else:
            self.last, self.failed_fixes = sig, 0   # the first failure is the problem itself, not a failed fix
        return self.failed_fixes >= self.limit

    def success(self) -> None:
        self.last, self.failed_fixes = None, 0
