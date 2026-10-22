"""WealthFlow QA Module - Settings > AI Advisor > Reasoning (thinking) (ai_think: auto | on | off, default auto).

Real browser, real settings API (no model needed: how the loop, the guide and the provider use the value is covered by the
Django tests with scripted providers):
  1. With no stored row the control shows the default "auto" and the API reports "auto".
  2. Choosing "off" and saving stores it on the server; the control still shows it after a reload.
  3. Restoring "auto" and saving brings the default back.
Every setting it changes is restored at the end.
"""

from tests.modules.e2e_settings import AI_ENGINE_PINS, fresh_state, pinned

SETTINGS_URL = "/api/settings/ai/"
_FETCH = """async ([url]) => { const res = await fetch(url); let data = null; try { data = await res.json(); } catch (e) {}
  return {status: res.status, data}; }"""


def _step(reporter, screenshot_logger, page, name, ok, detail, shot_name):
    shot = screenshot_logger.capture(page, "settings", shot_name, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "WealthFlow AI", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def _save(page):
    with page.expect_response(lambda r: SETTINGS_URL in r.url and r.request.method == "POST", timeout=15000):
        page.click("#aiSaveBtn")
    page.wait_for_timeout(600)


def _open(page, context):
    context.goto_route("#settings-aiadvisor")
    page.wait_for_selector("#aiThinkSelect", timeout=20000)


def _run(context, reporter, screenshot_logger):
    page = context.page
    context.goto_route("#settings-aiadvisor")
    page.reload()   # the page may still hold a form rendered before this step reset the setting (an earlier module's stale form)
    _open(page, context)
    page.wait_for_function(
        "() => document.getElementById('aiThinkSelect') && document.getElementById('aiThinkSelect').value === 'auto'",
        timeout=10000,
    )
    default = page.input_value("#aiThinkSelect")
    api_default = page.evaluate(_FETCH, [SETTINGS_URL])["data"].get("ai_think")
    _step(reporter, screenshot_logger, page, "AI Reasoning: default is auto", default == "auto" and api_default == "auto",
          f"control={default!r}, api={api_default!r}", "ai_think_default")
    page.select_option("#aiThinkSelect", "off")
    _save(page)
    stored = page.evaluate(_FETCH, [SETTINGS_URL])["data"].get("ai_think")
    page.reload()
    _open(page, context)
    after = page.input_value("#aiThinkSelect")
    _step(reporter, screenshot_logger, page, "AI Reasoning: off is saved and survives a reload", stored == "off" and after == "off",
          f"stored={stored!r}, control after reload={after!r}", "ai_think_off")
    page.select_option("#aiThinkSelect", "auto")
    _save(page)
    back = page.evaluate(_FETCH, [SETTINGS_URL])["data"].get("ai_think")
    _step(reporter, screenshot_logger, page, "AI Reasoning: auto restored", back == "auto", f"stored={back!r}", "ai_think_auto")


def test_ai_think_setting(context, reporter, screenshot_logger):
    try:
        with pinned({**AI_ENGINE_PINS}), fresh_state(["ai_think"]):
            _run(context, reporter, screenshot_logger)
    except Exception as ex:
        shot = screenshot_logger.capture(context.page, "settings", "ai_think_error", "none", "fail", "fail")
        reporter.add_step("AI Reasoning setting", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot)
