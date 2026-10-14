"""The `generate_file` AI tool: tells the app WHAT to put in the file the user asked for.

The model passes a `dataset` (a validated, owner-scoped database query), several `datasets`, a small `table` it wrote, or
text/code `content`; it never types the numbers of a dataset and never writes a link or path. The call is validated here
(so a wrong field name comes back to the model as a correctable error), and the app attaches the download link to the
answer; the file itself is rebuilt from these saved arguments when it is downloaded (see full_data.py)."""

from __future__ import annotations

from typing import Any

from .dataset import DatasetError, dataset_markdown
from .registry import all_formats, get_format
from .settings import get_settings

NAME = "generate_file"
MAX_DATASETS = 8
_S, _O, _A = ({"type": t} for t in ("string", "object", "array"))


def generate_file(user: Any, params: dict) -> dict:
    cfg = get_settings()
    if not cfg.enabled:
        return {"error": "File generation is switched off in Settings > AI Advisor."}
    fmt = get_format(params.get("format"))
    if fmt is None:
        return {"error": f"Unsupported format '{params.get('format')}'", "supported_formats": [f.key for f in all_formats()]}
    specs = params.get("datasets") if isinstance(params.get("datasets"), list) else ([params["dataset"]] if params.get("dataset") else [])
    table, content = params.get("table"), params.get("content")
    if not specs and not isinstance(table, dict) and not content:
        return {"error": "give a `dataset` (database query), a `table`, or text/code `content`"}
    if len(specs) > MAX_DATASETS:
        return {"error": f"at most {MAX_DATASETS} datasets per file"}
    rows = 0
    try:
        for spec in specs:
            rows += dataset_markdown(user, spec, cfg.max_rows)[1]
    except DatasetError as exc:
        return {"error": str(exc)}
    if isinstance(table, dict):
        if not isinstance(table.get("columns"), list) or not isinstance(table.get("rows"), list) or len(table["rows"]) > cfg.max_rows:
            return {"error": f"table must be {{columns: [...], rows: [[...]]}} with at most {cfg.max_rows} rows"}
        rows += len(table["rows"])
    return {"ok": True, "format": fmt.key, "rows": rows,
            "note": "The app attaches the download link itself right after your answer. Do NOT write a link or file name. "
                    "Tell the user briefly what the file contains."}


_DESC = ("Create a downloadable file for the user in this chat: Excel (xlsx), Word (docx), PDF (pdf), CSV, or text/code (txt md py js html css json sql). "
         "For data pass `dataset` (a database query: model, filters, fields, order_by, group_by, aggregate, total_columns, labels): the numbers come from "
         "the database, you never type them, and there is no 20-row cap. Use `datasets` for several tables. Use `table` only for a small table you "
         "composed yourself, and `content` for text or code. The app adds the download link to your answer.")
TOOL_DEF = {
    "name": NAME, "description": _DESC, "is_read_only": True, "tier": "read", "domain": "file_generation", "offer_always": True,
    "handler": lambda user, params: generate_file(user, params),
    "schema": {"type": "function", "function": {"name": NAME, "description": _DESC, "parameters": {"type": "object", "properties": {
        "format": {**_S, "description": "xlsx | docx | pdf | csv | txt | md | py | js | html | css | json | sql"},
        "filename": {**_S, "description": "name without folders (the app sanitises it)"},
        "title": {**_S, "description": "heading inside the file"},
        "dataset": {**_O, "description": "{model, filters:{field__lookup:value}, fields:[...], order_by:['-date'], group_by, aggregate:{sum:'amount'}, "
                    "total_columns:['amount'], labels:{field:'Header'}, limit}"},
        "datasets": {**_A, "description": "list of dataset objects: one table each (each may carry its own title)"},
        "table": {**_O, "description": "{columns:[...], rows:[[...]], totals:[...]} a small table you wrote"},
        "content": {**_S, "description": "text or code for the file (text/code formats), or notes for documents"},
    }, "required": ["format"]}}},
}
