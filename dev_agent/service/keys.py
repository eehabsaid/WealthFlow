"""API keys for the UIs: set, delete and 'is there one' - the value is never returned. The encrypted-file fallback needs the passphrase, which a UI
sends once (kept in memory only); with a working OS keyring it is never needed."""

from __future__ import annotations

from ..providers.registry import KEY_OPTIONAL, PROVIDERS
from ..settings.secrets import SecretsError, SecretStore


class Keys:
    def __init__(self, project, store=None):
        self._phrase = None
        self.store = store or SecretStore(forbid_under=project.root, passphrase=self._ask)

    def _ask(self, prompt: str, confirm: bool = False) -> str:
        if not self._phrase:
            raise SecretsError("passphrase_required")
        return self._phrase

    def unlock(self, passphrase: str) -> None:
        self._phrase = passphrase or None
        self.store._cached = None

    def get(self, name: str):
        return self.store.get(name)

    def status(self) -> dict:
        """{provider: True | False | None}: key stored / not stored / unknown because the credential file is locked. Never the value."""
        out = {}
        for name in sorted(PROVIDERS):
            if name in KEY_OPTIONAL:
                out[name] = True   # a local model needs no key
                continue
            try:
                out[name] = bool(self.store.get(name))
            except SecretsError:
                out[name] = None
        return out

    def set(self, provider: str, value: str) -> str:
        if provider not in PROVIDERS:
            raise SecretsError(f"unknown provider '{provider}'")
        return self.store.set(provider, value)

    def delete(self, provider: str) -> None:
        if provider not in PROVIDERS:
            raise SecretsError(f"unknown provider '{provider}'")
        self.store.delete(provider)
