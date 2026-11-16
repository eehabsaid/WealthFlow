"""Real-browser tests of the context meter and the "Context & limits" dialog against a real server with a fake model. Skipped when Chromium is missing."""

import json

import pytest

from ai.dev_agent.tests.apihelp import Api
from ai.dev_agent.tests.fakes import Scripted, final, plan, tool
from ai.dev_agent.tests.test_meter import Usage
from ai.dev_agent.tests.test_web_e2e import open_ui, send

sync_api = pytest.importorskip("playwright.sync_api")
expect = sync_api.expect


def saved(repo):
    return json.loads((repo.agent_dir / "agent_settings.json").read_text(encoding="utf-8"))


def shrink(api, window=50_000, reserve=10_000):
    status, _ = api.json("PUT", "/api/settings/context", {"values": {"context_window": window, "reserve_tokens": reserve}})
    assert status == 200


def test_the_meter_waits_for_the_first_model_call_then_shows_real_numbers(page, repo):
    provider = Usage([tool("read_file", path="app/calc.py"), final("it adds")], [(1_000, 40), (1_600, 20)])
    api = Api(repo, provider)
    try:
        shrink(api)
        open_ui(page, api)
        expect(page.locator("#context-meter")).to_contain_text("waiting for the first model call")
        expect(page.locator("#context-meter")).to_have_class("meter lvl-none")
        send(page, "how does add work?")
        page.wait_for_selector(".final")
        meter = page.locator("#context-meter")
        expect(meter).to_contain_text("1.6k / 50k")   # the last call: 1,600 prompt tokens + 20 reply tokens = 1,620 of the 50,000 window
        expect(meter).to_contain_text("3.2%")
        expect(meter).to_contain_text("48k left")
        expect(meter).to_have_class("meter lvl-ok")
        title = meter.get_attribute("title")
        assert "Context: 1,620 of 50,000 tokens (3.2%)" in title and "reported by the provider (prompt 1,600 + reply 20)" in title
        assert "before the agent trims old steps (at 40,000)" in title and "After plan, step 2" in title
        assert page.evaluate("document.querySelector('.meter-fill').style.width") == "3.2%"
        assert not page.errors, page.errors
    finally:
        api.close()


def test_the_meter_turns_amber_then_red_as_the_context_fills(page, repo):
    provider = Usage([tool("read_file", path="app/calc.py"), tool("read_file", path="app/util.py"), final("done")], [(8_000, 10), (33_000, 10), (39_500, 10)])
    api = Api(repo, provider)
    try:
        shrink(api)
        open_ui(page, api)
        send(page, "read two files")
        page.wait_for_selector(".final")
        meter = page.locator("#context-meter")
        expect(meter).to_have_class("meter lvl-critical")   # 39,510 of the 40,000 usable tokens
        expect(meter).to_contain_text("79%")
        assert "Nearly full: old steps are about to be trimmed." in meter.get_attribute("title")
        assert page.evaluate("getComputedStyle(document.querySelector('.meter-percent')).color") != page.evaluate("getComputedStyle(document.querySelector('.meter-used')).color")
    finally:
        api.close()


def test_an_estimate_is_marked_with_a_tilde(page, repo):
    api = Api(repo, Scripted([plan()]))   # the fake reports 10 + 5 tokens: far below the real size, so the agent's own estimate is shown
    try:
        open_ui(page, api)
        send(page, "add more")
        page.wait_for_selector("[data-act=approve]")
        expect(page.locator("#context-meter .meter-percent")).to_contain_text("~")
        assert "estimated by the agent" in page.locator("#context-meter").get_attribute("title")
    finally:
        api.close()


def test_the_dialog_shows_every_value_saves_a_change_and_reports_what_it_did(page, repo):
    api = Api(repo, Scripted([plan()]))
    try:
        open_ui(page, api)
        page.click("#context-settings-btn")
        page.wait_for_selector("#ctx-context_window")
        keys = page.eval_on_selector_all(".ctx-field input", "els => els.map(e => e.id.slice(4))")
        assert keys == ["context_window", "reserve_tokens", "max_output_tokens", "max_tool_result_chars", "max_steps_per_package", "max_fix_rounds", "timeout_s", "command_timeout_s"]
        assert page.input_value("#ctx-context_window") == "150000" and page.input_value("#ctx-max_steps_per_package") == "200"
        page.fill("#ctx-max_steps_per_package", "33")
        page.fill("#ctx-timeout_s", "10")
        page.click("#ctx-save")
        page.wait_for_selector(".ctx-settings .changes li")
        lines = page.inner_text(".ctx-settings .changes")
        assert "Max steps per phase: 200 → 33" in lines and "Model request timeout: 3,600 → 30 (you asked for 10; kept within limits: allowed range is 30 to 86,400)" in lines
        assert "Saved to coding_agent/agent_settings.json" in page.inner_text(".ctx-settings [role=status]")
        assert (saved(repo)["max_steps_per_package"], saved(repo)["timeout_s"]) == (33, 30)
        assert page.input_value("#ctx-timeout_s") == "30", "the field shows what was really saved"
        page.click("[value=close]")
        page.reload()
        page.wait_for_selector("#goal")
        page.click("#context-settings-btn")
        page.wait_for_selector("#ctx-max_steps_per_package")
        assert page.input_value("#ctx-max_steps_per_package") == "33", "survives a reload (the value lives in the file)"
        assert not page.errors, page.errors
    finally:
        api.close()


def test_the_dialog_rejects_bad_input_resets_to_defaults_and_warns_about_a_huge_reserve(page, repo):
    api = Api(repo, Scripted([plan()]))
    try:
        open_ui(page, api)
        page.click("#context-settings-btn")
        page.wait_for_selector("#ctx-timeout_s")
        before = (repo.agent_dir / "agent_settings.json").read_bytes() if (repo.agent_dir / "agent_settings.json").exists() else b""
        page.fill("#ctx-timeout_s", "")
        page.click("#ctx-save")
        assert "Every field needs a number." in page.inner_text(".ctx-settings [role=status]")
        page.fill("#ctx-timeout_s", "3600")
        page.click("#ctx-save")
        assert "Nothing changed." in page.inner_text(".ctx-settings [role=status]")
        after = (repo.agent_dir / "agent_settings.json").read_bytes() if (repo.agent_dir / "agent_settings.json").exists() else b""
        assert before == after, "nothing was written"
        page.fill("#ctx-reserve_tokens", "140000")
        page.click("#ctx-save")
        page.wait_for_selector(".ctx-settings .warnings li")
        assert "Only 10,000 of 150,000 tokens" in page.inner_text(".ctx-settings .warnings")
        assert saved(repo)["reserve_tokens"] == 140_000
        page.fill("#ctx-reserve_tokens", "149999")
        page.click("#ctx-save")
        expect(page.locator("#ctx-reserve_tokens")).to_have_value("145904")   # the field shows what the server really saved
        assert saved(repo)["reserve_tokens"] == 145_904 and "kept within limits" in page.inner_text(".ctx-settings .changes")
        page.click("[data-reset=reserve_tokens]")
        assert page.input_value("#ctx-reserve_tokens") == "28000"
    finally:
        api.close()
