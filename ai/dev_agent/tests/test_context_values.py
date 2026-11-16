"""Context settings: every value validated, clamped, written atomically to coding_agent/agent_settings.json, reported, and read again after a restart."""

import json

import pytest

from ai.dev_agent.settings import context_values as cv
from ai.dev_agent.settings.store import DEFAULTS, Settings, SettingsError
from ai.dev_agent.tests.apihelp import Api
from ai.dev_agent.tests.fakes import Scripted

KEYS = ["context_window", "reserve_tokens", "max_output_tokens", "max_tool_result_chars", "max_steps_per_package", "max_fix_rounds", "timeout_s", "command_timeout_s"]


def saved(repo):
    return json.loads((repo.agent_dir / "agent_settings.json").read_text(encoding="utf-8"))


def test_every_context_value_the_engine_reads_is_in_the_table():
    assert list(cv.SPEC) == KEYS
    rows = cv.describe(Settings.__new__(Settings) and {**DEFAULTS})
    assert [r["key"] for r in rows] == KEYS and all(r["min"] < r["max"] and r["help"] and r["default"] == DEFAULTS[r["key"]] for r in rows)
    assert all(r["min"] <= r["default"] <= r["max"] for r in rows), "the shipped defaults must be inside the allowed ranges"


def test_save_writes_only_the_asked_value_and_survives_a_restart(repo):
    out = cv.apply(repo, {"max_steps_per_package": 77})
    assert [(c["key"], c["old"], c["new"]) for c in out["changed"]] == [("max_steps_per_package", 200, 77)]
    assert out["file"] == "coding_agent/agent_settings.json" and "next task" in out["applies"]
    on_disk = saved(repo)
    assert on_disk["max_steps_per_package"] == 77 and on_disk["providers"]["ollama"]["base_url"] == DEFAULTS["providers"]["ollama"]["base_url"]
    assert {k: v for k, v in Settings(repo).load().items() if k != "max_steps_per_package"} == {k: v for k, v in DEFAULTS.items() if k != "max_steps_per_package"}
    assert Settings(repo).load()["max_steps_per_package"] == 77, "a fresh load (a restart) reads the saved value"
    assert not list(repo.agent_dir.glob("*.tmp")) and not [p for p in repo.agent_dir.iterdir() if p.name.startswith(".")], "no temp file is left behind"


def test_values_are_clamped_into_their_range_and_the_report_says_so(repo):
    out = cv.apply(repo, {"max_fix_rounds": 5000, "timeout_s": 1})
    rows = {c["key"]: c for c in out["changed"]}
    assert rows["max_fix_rounds"]["new"] == 100 and rows["max_fix_rounds"]["clamped"] and rows["max_fix_rounds"]["requested"] == 5000
    assert rows["timeout_s"]["new"] == 30 and "30" in rows["timeout_s"]["note"]
    assert saved(repo)["max_fix_rounds"] == 100


def test_the_reserve_cannot_swallow_the_window(repo):
    out = cv.apply(repo, {"reserve_tokens": 149_999})
    assert saved(repo)["reserve_tokens"] == 150_000 - cv.MIN_USABLE
    assert out["changed"][0]["clamped"] and "at least" in out["changed"][0]["note"]


def test_a_smaller_window_moves_the_reserve_and_the_report_lists_it(repo):
    cv.apply(repo, {"reserve_tokens": 100_000})
    out = cv.apply(repo, {"context_window": 32_768})
    rows = {c["key"]: c for c in out["changed"]}
    assert rows["context_window"]["new"] == 32_768 and rows["reserve_tokens"]["new"] == 32_768 - cv.MIN_USABLE and rows["reserve_tokens"]["clamped"]
    Settings(repo).load()   # the loader's own rule (reserve < window) holds


def test_the_reply_cap_cannot_exceed_the_window(repo):
    cv.apply(repo, {"context_window": 8192})
    assert saved(repo)["max_output_tokens"] == 8192
    assert cv.apply(repo, {"max_output_tokens": 999_999})["changed"] == []   # already at the window: nothing to change


def test_saving_one_value_never_rewrites_another_even_one_that_looks_odd(repo):
    """The real agent_settings.json has reserve 140000 of 150000 and replies up to 81920: saving a timeout must leave both alone and only warn."""
    cv.apply(repo, {"context_window": 150_000, "reserve_tokens": 140_000, "max_output_tokens": 81_920})
    out = cv.apply(repo, {"command_timeout_s": 900})
    assert [c["key"] for c in out["changed"]] == ["command_timeout_s"]
    on_disk = saved(repo)
    assert (on_disk["reserve_tokens"], on_disk["max_output_tokens"]) == (140_000, 81_920)
    assert any("Only 10,000 of 150,000 tokens" in w for w in out["warnings"])
    assert not any("reserve" in w and "overflow" in w for w in out["warnings"]), "81,920 fits into a 140,000 reserve"


def test_warnings_for_a_reply_cap_bigger_than_the_reserve(repo):
    out = cv.apply(repo, {"reserve_tokens": 20_000, "max_output_tokens": 30_000})
    assert any("can overflow" in w for w in out["warnings"]) and not any("Only" in w for w in out["warnings"])


def test_no_change_means_no_write(repo):
    cv.apply(repo, {"timeout_s": 1200})
    path = repo.agent_dir / "agent_settings.json"
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    out = cv.apply(repo, {"timeout_s": 1200, "max_fix_rounds": 12})
    assert out["changed"] == [] and {c["key"] for c in out["unchanged"]} == {"timeout_s", "max_fix_rounds"}
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before


@pytest.mark.parametrize("bad", [{}, None, {"nope": 1}, {"timeout_s": "abc"}, {"timeout_s": None}, {"timeout_s": True}, {"timeout_s": "nan"},
                                 {"timeout_s": "inf"}, {"timeout_s": [1]}, {"timeout_s": 60, "context_window": "x"}])
def test_invalid_input_changes_nothing(repo, bad):
    cv.apply(repo, {"timeout_s": 1000})
    path = repo.agent_dir / "agent_settings.json"
    before = path.read_bytes()
    with pytest.raises(SettingsError):
        cv.apply(repo, bad)
    assert path.read_bytes() == before


def test_numbers_may_be_typed_with_commas_or_as_decimals(repo):
    cv.apply(repo, {"context_window": "200,000", "timeout_s": 90.4})
    assert (saved(repo)["context_window"], saved(repo)["timeout_s"]) == (200_000, 90)


def test_http_get_and_put_with_the_real_server(repo):
    api = Api(repo, Scripted([]))
    try:
        status, body = api.json("GET", "/api/settings/context")
        assert status == 200 and [v["key"] for v in body["values"]] == KEYS and body["file"] == "coding_agent/agent_settings.json"
        status, body = api.json("PUT", "/api/settings/context", {"values": {"max_fix_rounds": 3, "timeout_s": 5}})
        assert status == 200 and {c["key"]: c["new"] for c in body["changed"]} == {"max_fix_rounds": 3, "timeout_s": 30}
        assert api.json("GET", "/api/settings/context")[1]["values"][5]["value"] == 3
        assert api.json("PUT", "/api/settings/context", {"values": {"timeout_s": "x"}})[0] == 400
        assert api.json("PUT", "/api/settings/context", {"values": {"model": 1}})[0] == 400
        assert api.json("PUT", "/api/settings/context", {"values": "x"})[0] == 400
        assert api.json("GET", "/api/settings/context", token="wrong")[0] == 401 and api.json("PUT", "/api/settings/context", {"values": {}}, token=None)[0] == 401
        assert api.json("GET", "/api/settings")[1]["max_fix_rounds"] == 3, "the older generic settings endpoint still works and sees the change"
        settings, _ = api.server.service._provider(None)
        assert settings["max_fix_rounds"] == 3, "the next task starts with the saved values"
    finally:
        api.close()
