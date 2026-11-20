"""Argument schemas of the tools written before native tool-calling existed (their text descriptions stay where the tools are defined)."""

from __future__ import annotations

from ai.dev_agent.tools.registry import REGISTRY, schema

STR_LIST = {"type": "array", "items": {"type": "string"}}
REPLACEMENT = {"type": "object", "properties": {"old": {"type": "string"}, "new": {"type": "string"}}, "required": ["old", "new"]}
EDIT = {"type": "object", "properties": {"path": {"type": "string"}, "replacements": {"type": "array", "items": REPLACEMENT}, "content": {"type": "string"},
                                          "overwrite": {"type": "boolean"}, "expect_sha": {"type": "string"}}, "required": ["path"]}

SCHEMAS = {
    "run_command": schema({"command": "string", "reason": "string"}, ["command"]),
    "git": schema({"args": STR_LIST}, ["args"]),
    "run_tests": schema({"files": STR_LIST, "modules": STR_LIST}),
    "note_proposal": schema({"path": "string", "text": "string"}, ["path", "text"]),
    "edit_files": schema({"edits": {"type": "array", "items": EDIT}}, ["edits"]),
    "delete_file": schema({"path": "string"}, ["path"]),
    "rename_file": schema({"from": "string", "to": "string"}, ["from", "to"]),
    "search_index": schema({"query": "string"}, ["query"]),
    "grep": schema({"pattern": {"type": "string", "description": "regular expression"}, "glob": {"type": "string", "description": "file pattern, e.g. *.py"}, "max_results": "integer"}, ["pattern"]),
    "read_file": schema({"path": "string", "start": {"type": "integer", "description": "first line (1-based)"}, "end": {"type": "integer", "description": "last line"}}, ["path"]),
    "plan_check": schema({"files": STR_LIST}, ["files"]),
    "remember": schema({"kind": {"type": "string", "enum": ["architecture", "rules", "lessons"]}, "text": "string", "evidence": STR_LIST}, ["kind", "text", "evidence"]),
}


def apply() -> None:
    for name, params in SCHEMAS.items():
        if name in REGISTRY:
            REGISTRY[name].params, REGISTRY[name].check_required = params, False
