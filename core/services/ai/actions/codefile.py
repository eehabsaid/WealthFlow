"""Confirmation cards for a code change proposed by the sysadmin's Agent (record = code_file). The write itself is core/services/ai/coding/edit.py."""

from __future__ import annotations

from core.services.ai.coding import edit

from .cards import make_card
from .common import ActionError

KEEP = ("op", "path", "content", "old_str", "new_str", "base_sha", "lines")


def _clip(text: str, n: int = 700) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


def propose_card(user, params: dict) -> dict:
    """Tool handler body (sysadmin / DEBUG already checked): validate the change and show the card. Nothing is written."""
    try:
        built = edit.build(params)
    except edit.EditError as exc:
        return {"error": str(exc)}
    rows = [{"label": "file", "value": built["path"]}, {"label": "lines", "value": built["lines"]}]
    rows.append({"label": "new file", "value": _clip(built["new"])} if built["op"] == "add" else {"label": "change", "before": _clip(built["old"]), "after": _clip(built["new"])})
    return make_card(user, {"record": "code_file", "op": built["op"], "params": {k: built[k] for k in KEEP if k in built}, "rows": rows})


def execute(user, op: str, params: dict) -> str:
    from core.services.ai.investigation.code_tools import code_access_allowed

    if not (edit.enabled() and code_access_allowed(user)):
        raise ActionError("Changing code is limited to the system administrator on the local development server.")
    try:
        return edit.apply({**params, "op": op})
    except edit.EditError as exc:
        raise ActionError(str(exc)) from None
