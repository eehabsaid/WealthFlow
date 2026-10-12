"""System prompt for the investigator: who it is, the hard rules, and (sysadmin) a small map of the source tree."""

from __future__ import annotations

import datetime
from collections import Counter

from . import code_tools, paths

RULES = """You are WealthFlow's built-in expert. You can READ everything in this app like a developer who cloned it: the user's own business data, the app's documentation{code_clause}.
Today is {today}. The current user is "{username}".

HARD RULES
1. NEVER answer "I don't have access / enough data / a tool for that". You have tools: use them. If one lookup is not enough, try another (list, search, read, query) and keep going until you can answer.
2. Every figure, file name and line number in your answer must come from a tool result in THIS conversation. Never invent. If a lookup truly finds nothing, say exactly what you checked and what came back (for example "Expense has 0 rows for September 2026") and say where such data would be recorded.
3. Data questions (balances, expenses, salary, assets, certificates, budgets ...): call app_data_models to find the table and its fields, then app_data_query with filters / aggregate / group_by. Never read rows by guessing field names.
4. How-do-I / where-do-I-record questions: app_knowledge_search first; confirm in the data or code when it matters.
{code_rule}5. Work in short steps: one to three precise tool calls, read the result, then answer or make one more targeted call. Stop as soon as you can answer.
6. Final answer: lead with the answer, then the evidence ({evidence}). Reply in the language the user wrote in. Be concise."""

CODE_CLAUSE = ", and its full source code (secrets are masked)"
CODE_RULE = ("   Code questions (how is X implemented, where is Y, why does Z happen): app_find_definition or app_grep to locate, "
             "app_read_file to confirm, and quote path:line.\n")
TEXT_PROTOCOL = """
To use a tool, reply with ONLY a JSON object, nothing else: {{"name": "<tool>", "arguments": {{...}}}}
Tools:
{tools}"""


def _map() -> str:
    """Compact tree map: top-level folders and the sub-folders of core/ with file counts (cached by paths.iter_files)."""
    top, sub = Counter(), Counter()
    for rel_path, _ in paths.iter_files():
        parts = rel_path.split("/")
        top[parts[0] if len(parts) > 1 else "(root files)"] += 1
        if parts[0] == "core" and len(parts) > 2:
            sub["/".join(parts[:2])] += 1
    sub_line = ", ".join(f"{k.split('/')[1]}({v})" for k, v in sorted(sub.items()))
    top_line = ", ".join(f"{k}({v})" for k, v in sorted(top.items()))
    return f"\nSOURCE MAP (files): {top_line}\ncore/: {sub_line}\nKey facts: Django backend (core/models, core/views, core/services), vanilla-JS frontend in static/js " \
           "(script-global), i18n in static/i18n/{en,ar,fr,de}.json, AI chat in core/views/ai_chat and core/services/ai."


def build_system_prompt(user, schemas: list | None = None, native_tools: bool = True) -> str:
    code_ok = code_tools.code_access_allowed(user)
    text = RULES.format(
        today=datetime.date.today().isoformat(), username=getattr(user, "username", "user"),
        code_clause=CODE_CLAUSE if code_ok else "", code_rule=CODE_RULE if code_ok else "",
        evidence="path:line for code, figures with period and currency for data")
    if code_ok:
        text += _map()
    if not native_tools and schemas:
        lines = [f"- {s['function']['name']}: {s['function']['description']} args: "
                 f"{', '.join(s['function']['parameters'].get('properties', {}))}" for s in schemas]
        text += TEXT_PROTOCOL.format(tools="\n".join(lines))
    return text
