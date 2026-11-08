"""coding_agent/agent_settings.json: provider, model, limits. Non-secret only; anything that looks like a credential is refused."""

from __future__ import annotations

import copy
import json
import re

from ..core import fsutil

DEFAULTS = {
    "provider": "ollama",
    "model": "",
    "providers": {
        "ollama": {"base_url": "http://127.0.0.1:11434"},
        "anthropic": {"base_url": "https://api.anthropic.com"},
        "openai": {"base_url": "https://api.openai.com/v1"},
        "gemini": {"base_url": "https://generativelanguage.googleapis.com"},
    },
    "context_window": 150000,
    "reserve_tokens": 28000,
    "max_output_tokens": 8192,
    "timeout_s": 3600,
    "command_timeout_s": 1800,
    "max_steps_per_package": 200,
    "max_fix_rounds": 12,
    "max_tool_result_chars": 8000,
}
SECRET_KEY = re.compile(r"(api[_-]?key|secret|password|passphrase|bearer|(^|[_-])(access[_-]?|auth[_-]?)?token$)", re.I)   # not "max_tokens"
SECRET_VALUE = re.compile(r"^(sk-[A-Za-z0-9_-]{16,}|AIza[0-9A-Za-z_-]{20,}|[A-Za-z0-9_-]{40,})$")
INTS = ("context_window", "reserve_tokens", "max_output_tokens", "timeout_s", "command_timeout_s", "max_steps_per_package", "max_fix_rounds", "max_tool_result_chars")


class SettingsError(ValueError):
    pass


def _scan(data, path=""):
    if isinstance(data, dict):
        for key, value in data.items():
            if SECRET_KEY.search(str(key)):
                raise SettingsError(f"'{path}{key}' looks like a credential; credentials go in the keyring (set-key), never in settings")
            _scan(value, f"{path}{key}.")
    elif isinstance(data, str) and SECRET_VALUE.match(data):
        raise SettingsError(f"value at '{path[:-1]}' looks like a credential; refusing to store it in settings")


def _merge(base: dict, extra: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in extra.items():
        out[key] = _merge(out[key], value) if isinstance(value, dict) and isinstance(out.get(key), dict) else value
    return out


def validate(data: dict) -> None:
    _scan(data)
    for key in INTS:
        if not isinstance(data.get(key), int) or isinstance(data.get(key), bool) or data[key] <= 0:
            raise SettingsError(f"{key} must be a positive integer")
    if data["reserve_tokens"] >= data["context_window"]:
        raise SettingsError("reserve_tokens must be smaller than context_window")
    if data["provider"] not in data["providers"]:
        raise SettingsError(f"unknown provider '{data['provider']}'")


class Settings:
    def __init__(self, project):
        self.project = project
        self.path = project.agent_dir / "agent_settings.json"

    def load(self) -> dict:
        try:
            stored = json.loads(self.path.read_text(encoding="utf-8"))
        except OSError:
            stored = {}
        except ValueError as exc:
            raise SettingsError(f"{self.path.name} is not valid JSON: {exc}") from exc
        data = _merge(DEFAULTS, stored)
        validate(data)
        return data

    def save(self, data: dict) -> None:
        validate(data)
        fsutil.atomic_write(self.path, (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))

    def update(self, values: dict) -> dict:
        """Apply several dotted-key changes (e.g. {"model": "x", "providers.ollama.base_url": "..."}); nothing is saved unless all are valid."""
        if not isinstance(values, dict) or not values:
            raise SettingsError("give the settings to change")
        data = self.load()
        for dotted, raw in values.items():
            node, keys = data, str(dotted).split(".")
            for key in keys[:-1]:
                if not isinstance(node.get(key), dict):
                    raise SettingsError(f"unknown setting '{dotted}'")
                node = node[key]
            if keys[-1] not in node or isinstance(node[keys[-1]], dict):
                raise SettingsError(f"unknown setting '{dotted}'")
            old = node[keys[-1]]
            try:
                node[keys[-1]] = int(raw) if isinstance(old, int) and not isinstance(old, bool) else str(raw)
            except (TypeError, ValueError) as exc:
                raise SettingsError(f"'{dotted}' must be a number") from exc
        self.save(data)
        return data

    def set(self, dotted: str, raw: str) -> dict:
        return self.update({dotted: raw})
