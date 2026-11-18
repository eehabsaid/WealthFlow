"""Non-code sources: locale JSON (en/ar/fr/de), page_descriptions.json, inventory.json (navigation) and Markdown docs."""

from __future__ import annotations

import json
import re

from ai.services.knowledge_index.config import LANGS
from ai.services.knowledge_index.parsers import make_symbol

_KEY_LINE = re.compile(r'^\s*"((?:[^"\\]|\\.)+)"\s*:')


def _key_lines(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for no, line in enumerate(text.splitlines(), 1):
        m = _KEY_LINE.match(line)
        if m:
            out.setdefault(m.group(1), no)
    return out


def _locale(rel: str, text: str):
    lang = rel.rsplit("/", 1)[-1][:-5]
    try:
        data = json.loads(text)
    except ValueError:
        return [make_symbol("<invalid-json>", "error", 1, 1)], []
    lines = _key_lines(text)
    kind = "i18n_key" if lang == "en" else "i18n_value"
    symbols = [make_symbol(k, kind, lines.get(k, 1), lines.get(k, 1), doc=f"{lang}: {v}"[:300], sig=f"{lang}={v}"[:200], body=str(v))
               for k, v in data.items() if isinstance(v, str)]
    for s in symbols:
        s["parent"] = lang if kind == "i18n_value" else ""
    return symbols, []


def _pages(rel: str, text: str):
    try:
        data = json.loads(text)
    except ValueError:
        return [make_symbol("<invalid-json>", "error", 1, 1)], []
    lines = _key_lines(text)
    if isinstance(data, dict):     # page_descriptions.json: "<route>[::<tab>]": {purpose, steps[]}
        return [make_symbol(k, "page_doc", lines.get(k, 1), lines.get(k, 1), doc=str(v.get("purpose", ""))[:300] if isinstance(v, dict) else "",
                            body=json.dumps(v, ensure_ascii=False)) for k, v in data.items()], []
    symbols, refs = [], []
    for page in data if isinstance(data, list) else []:   # inventory.json: pages with tabs
        if not isinstance(page, dict) or "route" not in page:
            continue
        line = lines.get('"route"', 1)
        symbols.append(make_symbol(str(page["route"]), "page_route", line, line, doc=str(page.get("title", "")) + " " + str(page.get("purpose", "")),
                                   body=json.dumps(page, ensure_ascii=False)))
        refs += [{"line": line, "src": str(page["route"]), "name": str(t.get("id") or t.get("name")), "kind": "tab"} for t in page.get("tabs", [])]
    for s in symbols:
        s["line"] = s["end"] = next((n for n, row in enumerate(text.splitlines(), 1) if f'"{s["name"]}"' in row), 1)
    return symbols, refs


def _markdown(text: str):
    heads = [(no, len(m.group(1)), m.group(2).strip()) for no, row in enumerate(text.splitlines(), 1) if (m := re.match(r"^(#{1,4})\s+(.*)", row))]
    lines, symbols = text.splitlines(), []
    for i, (no, _lvl, title) in enumerate(heads):
        end = (heads[i + 1][0] - 1) if i + 1 < len(heads) else len(lines)
        symbols.append(make_symbol(title[:100], "doc_section", no, end, body="\n".join(lines[no: min(end, no + 25)])))
    return symbols, []


def parse(rel: str, text: str):
    if rel.endswith(".md"):
        return _markdown(text)
    if rel.endswith(".json") and rel.rsplit("/", 1)[-1][:-5] in LANGS:
        return _locale(rel, text)
    return _pages(rel, text)
