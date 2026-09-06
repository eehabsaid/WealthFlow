"""
Recovery for a local-model tool-calling failure mode: instead of using real
structured function-calling, the model sometimes narrates its intent and
writes the call out as plain-text JSON, e.g.:

    To answer your question, I will use the `explain_chart` function...
    {"name": "explain_chart", "parameters": {"service_key": "gold"}}

Because this arrives as ordinary `content` rather than the API's `tool_calls`
field, the investigation loop (gated on `tool_calls_req` being non-empty)
never runs — the tool never actually executes, and this fabricated-looking
narration gets saved as the final answer with no real data behind it.

extract_fake_tool_call() scans content for a JSON object naming a real,
registered tool and returns a normalized tool_call dict ready to feed into
the existing execution pipeline (see ai_chat_loop.py / validate_and_execute_tool),
so the call still actually happens instead of being silently dropped.
"""

from __future__ import annotations

import json
import re
from typing import Any


def _extract_balanced_json(text: str, start: int) -> str:
    """Extracts the balanced {...} substring starting at index `start` (must be '{')."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return ""


def extract_fake_tool_call(content_str: str, valid_tool_names: set[str]) -> dict[str, Any] | None:
    """
    Returns {"name": ..., "arguments": {...}} if content_str contains a JSON
    object naming a registered tool (via "name"), else None. Accepts either
    "parameters" or "arguments" as the args key, since models mimicking the
    schema shape (which uses "parameters") are exactly the failure this
    guards against.
    """
    if not content_str or not valid_tool_names:
        return None

    for m in re.finditer(r"\{", content_str):
        obj_str = _extract_balanced_json(content_str, m.start())
        if not obj_str:
            continue
        try:
            obj = json.loads(obj_str)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue

        name = obj.get("name")
        if name not in valid_tool_names:
            continue

        args = obj.get("parameters") or obj.get("arguments") or {}
        if not isinstance(args, dict):
            args = {}

        return {"name": name, "arguments": args}

    return None
