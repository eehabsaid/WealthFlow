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

FILE_RULE = """
FILES: you CAN create files (Excel xlsx, Word docx, PDF, CSV, txt/code). When the user asks to export, download, save or "give me a file" of anything, call generate_file with a `dataset` (model, filters, fields, order_by, group_by, aggregate, total_columns): the numbers come straight from the database, there is no row cap, never type them yourself. Find the model and fields with app_data_models first. For a WRITTEN document (user guide, report, summary, explanation of the app) investigate with the tools, then call generate_file with the complete text in `content` (Markdown: # headings, lists, **bold**); do not announce that you will generate it, call the tool in the same reply. The app attaches the download link itself: never write a link, and never say you cannot create or send a file."""
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


AGENT_HEADER = """You are WealthFlow's built-in agent. You investigate the app with read-only tools and answer from facts, like a developer with the project open.
Today is {today}. The current user is "{username}". You can read: the user's own business data, the app's documentation and screens{code_clause}.

"""


def _tail(user, schemas, native_tools, code_ok) -> str:
    from core.services.ai.exports.settings import exports_enabled

    text = (FILE_RULE if exports_enabled() else "") + (_map() if code_ok else "")
    if not native_tools and schemas:
        lines = [f"- {s['function']['name']}: {s['function']['description']} args: "
                 f"{', '.join(s['function']['parameters'].get('properties', {}))}" for s in schemas]
        text += TEXT_PROTOCOL.format(tools="\n".join(lines))
    return text


def build_agent_prompt(user, schemas: list | None = None, native_tools: bool = True, instructions: str | None = None) -> str:
    """Agent mode: fixed header + the editable instructions (Settings > AI Advisor; default in agent/instructions.py)."""
    from core.services.ai.agent.instructions import effective_instructions

    code_ok = code_tools.code_access_allowed(user)
    head = AGENT_HEADER.format(today=datetime.date.today().isoformat(), username=getattr(user, "username", "user"),
                               code_clause=CODE_CLAUSE if code_ok else "")
    return head + (instructions or effective_instructions()) + _tail(user, schemas, native_tools, code_ok)


def build_system_prompt(user, schemas: list | None = None, native_tools: bool = True) -> str:
    code_ok = code_tools.code_access_allowed(user)
    text = RULES.format(
        today=datetime.date.today().isoformat(), username=getattr(user, "username", "user"),
        code_clause=CODE_CLAUSE if code_ok else "", code_rule=CODE_RULE if code_ok else "",
        evidence="path:line for code, figures with period and currency for data")
    return text + _tail(user, schemas, native_tools, code_ok)
