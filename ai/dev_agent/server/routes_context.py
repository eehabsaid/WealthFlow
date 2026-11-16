"""Context settings for the settings UI: GET lists every context value with its range, PUT validates, clamps and writes them (see settings/context_values.py)."""

from __future__ import annotations

import re

from ai.dev_agent.settings import context_values
from ai.dev_agent.settings.store import Settings


def get_context(r):
    data = Settings(r.project).load()
    return {"file": f"{r.project.agent_dir.name}/agent_settings.json", "values": context_values.describe(data), "warnings": context_values.warnings(data),
            "applies": context_values.APPLIES}


def put_context(r):
    return context_values.apply(r.project, r.field("values", dict))


ROUTES = [
    ("GET", re.compile(r"/api/settings/context"), get_context),
    ("PUT", re.compile(r"/api/settings/context"), put_context),
]
