"""Pick the configured provider and model; the user chooses both in agent_settings.json. Credentials come from the SecretStore only."""

from __future__ import annotations

from ai.dev_agent.providers.adapters import Anthropic, Gemini, Ollama, OpenAI
from ai.dev_agent.providers.base import Provider, ProviderError

PROVIDERS = {"ollama": Ollama, "anthropic": Anthropic, "openai": OpenAI, "gemini": Gemini}
KEY_OPTIONAL = {"ollama"}


def build_provider(settings: dict, secrets) -> Provider:
    name = settings["provider"]
    if name not in PROVIDERS:
        raise ProviderError(f"unknown provider '{name}'")
    if not settings.get("model"):
        raise ProviderError("no model chosen: run `python -m ai.dev_agent settings set model <name>`")
    key = secrets.get(name) or ""
    if not key and name not in KEY_OPTIONAL:
        raise ProviderError(f"no API key stored for {name}: run `python -m ai.dev_agent set-key {name}`")
    return PROVIDERS[name](settings["model"], settings["providers"][name]["base_url"], key, settings["timeout_s"],
                           settings["max_output_tokens"], settings["context_window"])
