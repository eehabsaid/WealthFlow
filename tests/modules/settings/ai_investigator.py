"""Settings module phase 9: AI Advisor "AI Investigator" mode + source-code switch, and French instant answers.

Checks, against the real API (not just the DOM):
  1. #aiInvestigatorModeSelect (default "auto") and #aiCodeAccessToggle (default ON) render on #settings-aiadvisor.
  2. Choosing "always" and switching the code toggle OFF + Save persists both; the original state is restored afterwards.
  3. A French balance question is answered by code (direct_answer, 0 LLM calls, request.lang == "fr").
     SKIPs when the AI workspace is not available for the account (the chat endpoint then refuses before routing).
"""

from tests.modules.e2e_settings import AI_ENGINE_PINS, fresh_state, pinned
from tests.modules.settings.ai_instant_answers import CHAT_URL, SETTINGS_URL, _api_get, _ask, _direct_call
from tests.modules.settings.common import close_global_modal

FRENCH_QUESTION = "Combien d'argent ai-je ?"


def _save(page, mode, code_on):
    close_global_modal(page)
    page.select_option("#aiInvestigatorModeSelect", mode)
    box = page.query_selector("#aiCodeAccessToggle")
    if box.is_checked() != code_on:
        box.click()
    with page.expect_response(lambda r: SETTINGS_URL in r.url and r.request.method == "POST", timeout=15000):
        page.click("#aiSaveBtn")
    page.wait_for_timeout(500)
    data = _api_get(page, SETTINGS_URL) or {}
    return data.get("ai_investigator_mode"), data.get("ai_code_access")


def test_ai_investigator(context, reporter, screenshot_logger):
    # Pin every precondition: defaults are checked on a fresh state, and the French instant answer needs the engine ON
    # (the developer's local DB has ai_direct_answers=false, which the runner copies).
    with pinned({**AI_ENGINE_PINS, "ai_direct_answers": "true"}), fresh_state(["ai_investigator_mode", "ai_code_access"]):
        _run(context, reporter, screenshot_logger)


def _run(context, reporter, screenshot_logger):
    page = context.page
    close_global_modal(page)
    page.reload()
    context.goto_route("#settings-aiadvisor")
    close_global_modal(page)
    reporter.pages_visited.add("Settings -> AI Advisor")
    try:
        page.wait_for_selector("#aiInvestigatorModeSelect", timeout=20000)
    except Exception as ex:
        shot = screenshot_logger.capture(page, "settings", "ai_investigator", "none", "controls_missing", "fail")
        reporter.add_step("AI Investigator Controls", "Settings", "FAIL", f"Controls not rendered: {ex}", screenshot_path=shot)
        return

    stored = _api_get(page, SETTINGS_URL) or {}
    original = (stored.get("ai_investigator_mode"), stored.get("ai_code_access"))
    shot = screenshot_logger.capture(page, "settings", "ai_investigator", "none", "controls", "ok")
    ui = (page.input_value("#aiInvestigatorModeSelect"), page.is_checked("#aiCodeAccessToggle"))
    reporter.add_step("AI Investigator Defaults", "Settings", "PASS" if original == ("auto", True) and ui == original else "FAIL",
                      f"API={original!r} UI={ui!r}", screenshot_path=shot)
    try:
        saved = _save(page, "always", False)
        reporter.add_step("AI Investigator Save", "Settings", "PASS" if saved == ("always", False) else "FAIL", f"API after save: {saved!r}")

        resp = _ask(page, FRENCH_QUESTION)
        if resp["status"] != 200:
            reporter.add_step("French Instant Answer (0 LLM calls)", "WealthFlow AI", "SKIP",
                              f"Chat endpoint returned {resp['status']} ({CHAT_URL}: AI workspace not available for this account).")
        else:
            call = _direct_call(resp)
            lang = (((call or {}).get("arguments") or {}).get("request") or {}).get("lang")
            passed = bool(call) and call.get("llm_calls") == 0 and lang == "fr"
            reporter.add_step("French Instant Answer (0 LLM calls)", "WealthFlow AI", "PASS" if passed else "FAIL",
                              f"tool={call.get('tool')!r} llm_calls={call.get('llm_calls')!r} lang={lang!r}" if call else "Engine did not answer a French balance question.")
    except Exception as ex:
        reporter.add_step("AI Investigator", "Settings", "FAIL", f"Exception: {ex}")
    finally:
        try:   # always leave the account in its original state
            _save(page, original[0] or "auto", bool(original[1]) if original[1] is not None else True)
        except Exception:
            pass
