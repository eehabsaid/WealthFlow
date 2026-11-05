import base64
import json

import pytest

from ..settings.secrets import SecretsError, SecretStore
from ..settings.store import Settings, SettingsError

N = 2 ** 10   # cheap scrypt for tests; the default is 2**15


class FakeKeyring:
    def __init__(self, broken=False):
        self.data, self.broken = {}, broken

    def set_password(self, service, name, value):
        if self.broken:
            raise RuntimeError("locked")
        self.data[(service, name)] = value

    def get_password(self, service, name):
        if self.broken:
            raise RuntimeError("locked")
        return self.data.get((service, name))

    def delete_password(self, service, name):
        self.data.pop((service, name), None)


def store(tmp_path, keyring=None, phrase="correct horse battery"):
    return SecretStore(tmp_path / "s.enc", passphrase=lambda p, c=False: phrase, keyring_module=keyring, kdf_n=N)


def test_keyring_is_primary_and_no_file_is_created(tmp_path):
    kr = FakeKeyring()
    s = store(tmp_path, kr)
    assert s.set("openai", "sk-abc") == "keyring" and s.get("openai") == "sk-abc"
    assert not (tmp_path / "s.enc").exists() and s.backend == "keyring"


def test_falls_back_to_encrypted_file_when_keyring_broken_or_missing(tmp_path):
    assert store(tmp_path, FakeKeyring(broken=True)).set("a", "v1") == "encrypted file"
    s = store(tmp_path, None)
    assert s.set("b", "v2") == "encrypted file" and s.get("a") == "v1" and s.get("b") == "v2" and s.backend == "encrypted file"


def test_file_holds_no_plaintext_and_no_key_material(tmp_path):
    s = store(tmp_path, None)
    s.set("anthropic", "sk-ant-SECRETVALUE-123456")
    raw = (tmp_path / "s.enc").read_text()
    assert "SECRETVALUE" not in raw and "anthropic" not in raw and "correct horse" not in raw
    blob = json.loads(raw)
    assert set(blob) == {"v", "kdf", "n", "r", "p", "salt", "nonce", "ct"} and blob["kdf"] == "scrypt"


def test_wrong_passphrase_fails_cleanly_and_never_overwrites(tmp_path):
    store(tmp_path, None).set("a", "v1")
    before = (tmp_path / "s.enc").read_bytes()
    bad = store(tmp_path, None, phrase="another passphrase!!")
    with pytest.raises(SecretsError, match="wrong passphrase"):
        bad.get("a")
    with pytest.raises(SecretsError):
        bad.set("b", "x")
    assert (tmp_path / "s.enc").read_bytes() == before


def test_tampered_file_is_detected(tmp_path):
    s = store(tmp_path, None)
    s.set("a", "v1")
    blob = json.loads((tmp_path / "s.enc").read_text())
    ct = bytearray(base64.b64decode(blob["ct"]))
    ct[0] ^= 1
    blob["ct"] = base64.b64encode(bytes(ct)).decode()
    (tmp_path / "s.enc").write_text(json.dumps(blob))
    with pytest.raises(SecretsError):
        store(tmp_path, None).get("a")


def test_fresh_salt_and_nonce_on_every_save(tmp_path):
    s = store(tmp_path, None)
    s.set("a", "v1")
    first = json.loads((tmp_path / "s.enc").read_text())
    s.set("a", "v1")
    second = json.loads((tmp_path / "s.enc").read_text())
    assert first["salt"] != second["salt"] and first["nonce"] != second["nonce"] and first["ct"] != second["ct"]


def test_weak_passphrase_rejected_when_creating(tmp_path):
    with pytest.raises(SecretsError, match="at least"):
        store(tmp_path, None, phrase="short").set("a", "v")


def test_file_inside_repo_is_refused(tmp_path):
    with pytest.raises(SecretsError, match="outside the project"):
        SecretStore(tmp_path / "repo" / "x.enc", forbid_under=tmp_path / "repo")


def test_delete_and_empty_value(tmp_path):
    s = store(tmp_path, None)
    s.set("a", "v1")
    s.set("b", "v2")
    s.delete("a")
    assert s.get("a") is None and s.get("b") == "v2"
    with pytest.raises(SecretsError):
        s.set("c", "")


def test_settings_defaults_roundtrip_and_set(repo):
    st = Settings(repo)
    assert st.load()["provider"] == "ollama"
    st.set("model", "qwen2.5-coder:14b")
    st.set("context_window", "100000")
    st.set("providers.ollama.base_url", "http://localhost:9999")
    data = st.load()
    assert data["model"] == "qwen2.5-coder:14b" and data["context_window"] == 100000 and data["providers"]["ollama"]["base_url"] == "http://localhost:9999"
    assert data["providers"]["openai"]["base_url"]   # untouched defaults survive the merge


@pytest.mark.parametrize("key,value", [("nope", "x"), ("providers.zzz.base_url", "x"), ("provider", "bard"), ("reserve_tokens", "999999"), ("timeout_s", "0")])
def test_settings_reject_bad_values(repo, key, value):
    with pytest.raises(SettingsError):
        Settings(repo).set(key, value)


def test_settings_refuse_credentials(repo):
    st = Settings(repo)
    data = st.load()
    data["providers"]["openai"]["api_key"] = "x"
    with pytest.raises(SettingsError, match="credential"):
        st.save(data)
    with pytest.raises(SettingsError, match="credential"):
        st.set("model", "sk-" + "a" * 30)
    assert not (repo.agent_dir / "agent_settings.json").exists() or "sk-" not in (repo.agent_dir / "agent_settings.json").read_text()


def test_invalid_settings_file_reports_clearly(repo):
    (repo.agent_dir / "agent_settings.json").write_text("{nope", encoding="utf-8")
    with pytest.raises(SettingsError, match="not valid JSON"):
        Settings(repo).load()
