"""Behavior switches for the settings UI: GET lists them, PUT changes some (see settings/behavior.py)."""

from __future__ import annotations

import re

from ai.dev_agent.settings import behavior
from ai.dev_agent.settings.store import Settings


def get_behavior(r):
    return {"file": f"{r.project.agent_dir.name}/agent_settings.json", "values": behavior.describe(Settings(r.project).load()), "applies": behavior.APPLIES}


def put_behavior(r):
    return behavior.apply(r.project, r.field("values", dict))


ROUTES = [
    ("GET", re.compile(r"/api/settings/behavior"), get_behavior),
    ("PUT", re.compile(r"/api/settings/behavior"), put_behavior),
]
