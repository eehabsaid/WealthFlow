"""Credential storage. Primary: the OS keyring (Windows Credential Manager, macOS Keychain, Secret Service). Fallback: one encrypted file
outside the repo. The file key is derived from a user passphrase with scrypt and is NEVER stored; every save uses a fresh salt and nonce."""

from __future__ import annotations

import base64
import getpass
import hashlib
import json
import os
from pathlib import Path

from ai.dev_agent.core import fsutil

SERVICE = "dev_agent"
MIN_PASSPHRASE = 12
MAGIC = b"dev_agent-secrets-v1"


class SecretsError(RuntimeError):
    pass


def default_file() -> Path:
    base = os.environ.get("APPDATA")   # Windows: %APPDATA%\dev_agent
    return Path(base) / "dev_agent" / "secrets.enc" if base else Path.home() / ".dev_agent" / "secrets.enc"


def prompt_passphrase(prompt: str, confirm: bool = False) -> str:
    env = os.environ.get("DEV_AGENT_PASSPHRASE")
    if env:
        return env
    first = getpass.getpass(prompt)
    if confirm and getpass.getpass("Repeat passphrase: ") != first:
        raise SecretsError("passphrases do not match")
    return first


def _key(passphrase: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(passphrase.encode("utf-8"), salt=salt, n=n, r=r, p=p, maxmem=512 * 1024 * 1024, dklen=32)


def _aes():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:
        raise SecretsError("the encrypted-file fallback needs the 'cryptography' package (already in WealthFlow's requirements)") from exc
    return AESGCM


def _auto_keyring():
    try:
        import keyring
        from keyring.backends import fail
    except ImportError:
        return None
    backend = keyring.get_keyring()
    return None if isinstance(backend, fail.Keyring) or getattr(backend, "priority", 0) <= 0 else keyring


class SecretStore:
    def __init__(self, file_path=None, passphrase=prompt_passphrase, keyring_module="auto", forbid_under=None, kdf_n: int = 2 ** 15):
        self.file = Path(file_path) if file_path else default_file()
        if forbid_under and self.file.resolve().is_relative_to(Path(forbid_under).resolve()):
            raise SecretsError("the credential file must live outside the project repository")
        self._passphrase = passphrase
        self._keyring = _auto_keyring() if keyring_module == "auto" else keyring_module
        self.kdf_n = kdf_n
        self._cached = None

    @property
    def backend(self) -> str:
        return "keyring" if self._keyring else "encrypted file"

    def _phrase(self, creating: bool) -> str:
        if self._cached is None:
            phrase = self._passphrase("Credential file passphrase: ", creating)
            if creating and len(phrase) < MIN_PASSPHRASE:
                raise SecretsError(f"use a passphrase of at least {MIN_PASSPHRASE} characters")
            self._cached = phrase
        return self._cached

    def _read_file(self) -> dict:
        if not self.file.is_file():
            return {}
        try:
            blob = json.loads(self.file.read_text(encoding="utf-8"))
            salt, nonce, ct = (base64.b64decode(blob[k]) for k in ("salt", "nonce", "ct"))
            key = _key(self._phrase(False), salt, blob["n"], blob["r"], blob["p"])
            return json.loads(_aes()(key).decrypt(nonce, ct, MAGIC).decode("utf-8"))
        except SecretsError:
            raise
        except Exception as exc:   # wrong passphrase and corrupt file look the same on purpose
            self._cached = None
            raise SecretsError("could not decrypt the credential file (wrong passphrase or damaged file)") from exc

    def _write_file(self, data: dict) -> None:
        salt, nonce = os.urandom(16), os.urandom(12)
        key = _key(self._phrase(not self.file.exists()), salt, self.kdf_n, 8, 1)
        ct = _aes()(key).encrypt(nonce, json.dumps(data).encode("utf-8"), MAGIC)
        blob = {"v": 1, "kdf": "scrypt", "n": self.kdf_n, "r": 8, "p": 1,
                "salt": base64.b64encode(salt).decode(), "nonce": base64.b64encode(nonce).decode(), "ct": base64.b64encode(ct).decode()}
        fsutil.atomic_write(self.file, json.dumps(blob).encode("utf-8"))
        try:
            os.chmod(self.file, 0o600)
        except OSError:
            pass

    def set(self, name: str, value: str) -> str:
        if not value:
            raise SecretsError("empty credential")
        if self._keyring:
            try:
                self._keyring.set_password(SERVICE, name, value)
                return "keyring"
            except Exception:   # keyring present but unusable (locked, no backend): fall back
                pass
        data = self._read_file()
        data[name] = value
        self._write_file(data)
        return "encrypted file"

    def get(self, name: str) -> str | None:
        if self._keyring:
            try:
                value = self._keyring.get_password(SERVICE, name)
                if value:
                    return value
            except Exception:
                pass
        return self._read_file().get(name) if self.file.is_file() else None

    def delete(self, name: str) -> None:
        if self._keyring:
            try:
                self._keyring.delete_password(SERVICE, name)
            except Exception:
                pass
        if self.file.is_file():
            data = self._read_file()
            if data.pop(name, None) is not None:
                self._write_file(data)
