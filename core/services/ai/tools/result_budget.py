"""Token-budget the tool result before it is appended to the model conversation.

The assembled chat context is capped by ai_context_token_budget, but run_tool_investigation_loop
appended json.dumps(tool_res) with no cap: at ~45 tok/s prefill, every 1k tokens of result is
~22 s of wait, and up to MAX_TOOL_ITERATIONS results accumulate. Shrinks the largest lists first
(lists are newest-first, so the head is kept), never touches short scalars or the `instructions`
accuracy rule, and records what was cut so the model does not present a partial list as complete."""

from __future__ import annotations

import copy
import json
from typing import Any

_PROTECTED_KEYS = {"instructions", "_truncation", "_explanation_metadata"}
_MIN_CHARS = 4000
_MAX_PASSES = 60
_MAX_STR = 400


def tool_result_max_chars() -> int:
    from core.models import AppSettings

    try:
        tokens = int(AppSettings.get("ai_context_token_budget", "2048"))
    except (TypeError, ValueError):
        tokens = 2048
    return max(_MIN_CHARS, tokens * 4)


def _dumps(obj: Any) -> str:
    return json.dumps(obj, default=str, ensure_ascii=False, separators=(",", ":"))


def _largest_list(node: Any, path: str, best: list, depth: int = 0) -> None:
    if depth > 4:
        return
    if isinstance(node, dict):
        for k, v in node.items():
            if k in _PROTECTED_KEYS:
                continue
            _largest_list(v, f"{path}.{k}" if path else str(k), best, depth + 1)
    elif isinstance(node, list):
        if len(node) > 1:
            size = len(_dumps(node))
            if not best or size > best[0][0]:
                best[:] = [(size, path, node)]
        for i, v in enumerate(node[:1]):
            _largest_list(v, f"{path}[{i}]", best, depth + 1)


def _clip_long_strings(node: Any, depth: int = 0) -> Any:
    if depth > 6:
        return node
    if isinstance(node, dict):
        return {k: (v if k in _PROTECTED_KEYS else _clip_long_strings(v, depth + 1)) for k, v in node.items()}
    if isinstance(node, list):
        return [_clip_long_strings(v, depth + 1) for v in node]
    if isinstance(node, str) and len(node) > _MAX_STR:
        return node[:_MAX_STR] + "…"
    return node


def compact_tool_result(result: Any, max_chars: int | None = None) -> str:
    """JSON string of `result`, at most ~max_chars long (plus a short truncation note)."""
    limit = max_chars or tool_result_max_chars()
    text = _dumps(result)
    if len(text) <= limit or not isinstance(result, dict):
        return text if len(text) <= limit else text[:limit] + '…[TRUNCATED]'

    work = copy.deepcopy(result)
    cuts: dict[str, dict[str, int]] = {}
    for _ in range(_MAX_PASSES):
        best: list = []
        _largest_list(work, "", best)
        if not best:
            break
        _, path, lst = best[0]
        keep = max(1, len(lst) // 2)
        entry = cuts.setdefault(path, {"of": len(lst) if path not in cuts else cuts[path]["of"], "kept": keep})
        entry["kept"] = keep
        del lst[keep:]
        if len(_dumps({**work, "_truncation": cuts})) <= limit:
            break
    else:
        pass

    if len(_dumps({**work, "_truncation": cuts})) > limit:
        work = _clip_long_strings(work)
    if cuts:
        work["_truncation"] = {
            "note": "Lists were cut to fit the token budget (newest items kept first). "
                    "Do not present them as complete.",
            "lists": cuts,
        }
    final = _dumps(work)
    return final if len(final) <= limit + 600 else final[:limit] + "…[TRUNCATED]"
