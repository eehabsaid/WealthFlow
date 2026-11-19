"""How much one lookup may return. Normal: the strict defaults. With the `deep_search` switch (Settings > Behavior) the read-only tools return more per call,
so the model finds the right files in fewer steps."""

from __future__ import annotations

NORMAL = {"read_lines": 400, "index_results": 15, "grep_default": 50, "grep_cap": 200, "result_factor": 1, "repeat_stop": 4}
DEEP = {"read_lines": 1200, "index_results": 40, "grep_default": 100, "grep_cap": 600, "result_factor": 3, "repeat_stop": 6}


def of(settings: dict) -> dict:
    return DEEP if (settings or {}).get("deep_search") else NORMAL
