"""Settings module phase 8: per-user AI Advisor settings ("My AI Settings") + sysadmin monthly token limits.

Drives the real UI and verifies every result through the API:
  1. #settings-myai renders; the "Use general app settings" switch is ON by default and the own-settings fieldset is locked.
  2. Sysadmin-only fields (permission tier, read-only, multi-agent, Ollama URL, pipeline switches) are NOT in the DOM.
  3. Switch OFF + own model + Save persists use_general=false and the model; no sysadmin key is written.
  4. Switch back ON + Save restores use_general=true (own values are kept but ignored).
  5. The sysadmin limits panel renders on #settings-aiadvisor above the platform card, with the app's Save button style;
     default limit and a per-user override round-trip through the UI.
  6. Search/filter, Toggle Select All + bulk apply (all eligible users), and the shared Show all / Show less rows toggle.
The account's original settings and limits are always restored.
"""

from tests.modules.settings.common import close_global_modal

ME_URL = "/api/settings/ai/me/"
LIMITS_URL = "/api/settings/ai/user-limits/"
BANNED_IDS = ["ai_permission_tier", "aiPermissionTierSelect", "ai_read_only", "aiMultiAgentToggle", "ai_ollama_url",
              "ai_openai_base_url", "ai_azure_endpoint", "aiPipelineDebugToggle", "aiValidateModeSelect"]
_GET = "async (u) => { const r = await fetch(u); return r.ok ? await r.json() : null; }"
_POST = """async ([url, body]) => {
    const token = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
    const r = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': token}, body: JSON.stringify(body)});
    return r.status;
}"""


def _step(reporter, shots, page, name, ok, detail, shot_name):
    shot = shots.capture(page, "settings", shot_name, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "Settings", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def _save_me(page):
    with page.expect_response(lambda r: ME_URL in r.url and r.request.method == "POST", timeout=20000):
        page.click("#myAISaveBtn")
    page.wait_for_selector("#myAIUseGeneral", timeout=15000)
    page.wait_for_timeout(400)


def _my_settings(context, reporter, shots):
    page = context.page
    original = page.evaluate(_GET, ME_URL) or {}
    try:
        context.goto_route("#settings-myai")
        reporter.pages_visited.add("Settings -> My AI Settings")
        page.wait_for_selector("#myAIUseGeneral", timeout=20000)
        locked = page.eval_on_selector("#myAIOwn", "el => el.disabled")
        _step(reporter, shots, page, "My AI Settings tab renders (general switch, own fields locked)",
              page.is_checked("#myAIUseGeneral") == bool(original.get("use_general")) and locked == bool(original.get("use_general")),
              f"api use_general={original.get('use_general')} checked={page.is_checked('#myAIUseGeneral')} locked={locked}", "myai_tab")

        present = [i for i in BANNED_IDS if page.query_selector(f"#{i}")]
        _step(reporter, shots, page, "My AI Settings hides sysadmin-only fields", not present, f"unexpected fields: {present}", "myai_no_admin_fields")

        if page.is_checked("#myAIUseGeneral"):
            page.click("#myAIUseGeneral")
        page.select_option("#ai_provider", "ollama")
        page.uncheck("#ai_enabled")   # avoids the post-save connection test
        page.fill("#ai_model", "e2e-own-model")
        _save_me(page)
        mine = page.evaluate(_GET, ME_URL) or {}
        _step(reporter, shots, page, "Own AI settings save (switch OFF) persists",
              mine.get("use_general") is False and mine.get("fields", {}).get("ai_model") == "e2e-own-model",
              f"use_general={mine.get('use_general')} model={mine.get('fields', {}).get('ai_model')!r} effective={mine.get('effective')}", "myai_saved_own")

        page.click("#myAIUseGeneral")
        _save_me(page)
        back = page.evaluate(_GET, ME_URL) or {}
        _step(reporter, shots, page, "Switch back to general settings restores shared config",
              back.get("use_general") is True and back.get("effective", {}).get("ai_model") != "e2e-own-model",
              f"use_general={back.get('use_general')} effective={back.get('effective')}", "myai_back_general")
    finally:
        close_global_modal(page)
        if original:   # restore: a user who was on own settings gets that mode back
            page.evaluate(_POST, [ME_URL, {"use_general": bool(original.get("use_general", True)),
                                           **({} if original.get("use_general", True) else
                                              {k: v for k, v in original.get("fields", {}).items() if "api_key" not in k})}])


def _limits(context, reporter, shots):
    page = context.page
    before = page.evaluate(_GET, LIMITS_URL)
    context.goto_route("#settings-aiadvisor")
    reporter.pages_visited.add("Settings -> AI Advisor (limits)")
    try:
        page.wait_for_selector("#aiDefaultLimitInput", timeout=20000)
    except Exception as ex:
        _step(reporter, shots, page, "AI token limits panel renders", False, f"panel missing: {ex}", "ai_limits_missing")
        return
    _step(reporter, shots, page, "AI token limits panel renders", before is not None, f"users={len((before or {}).get('users', []))}", "ai_limits_panel")
    original_default = (before or {}).get("default_limit", "0")
    try:
        page.fill("#aiDefaultLimitInput", "123456")
        with page.expect_response(lambda r: LIMITS_URL in r.url and r.request.method == "POST", timeout=15000):
            page.click("#aiDefaultLimitSave")
        page.wait_for_selector("#aiDefaultLimitInput", timeout=10000)
        after = page.evaluate(_GET, LIMITS_URL + "?page_size=200") or {}
        _step(reporter, shots, page, "Default monthly token limit saves via UI", str(after.get("default_limit")) == "123456",
              f"default_limit={after.get('default_limit')!r}", "ai_limits_default")

        _layout_and_bulk(context, reporter, shots, after)
        row = page.query_selector("#aiLimitsBody tr:has(.ai-limit-input:not([disabled]))")
        if row is None:
            reporter.add_step("Per-user token limit override", "Settings", "SKIP", "No user on general settings in this environment.")
            return
        uid = int(row.get_attribute("data-user-id"))
        orig_row = next((u for u in (after.get("users") or []) if u["id"] == uid), {})
        row.query_selector(".ai-limit-input").fill("50")
        with page.expect_response(lambda r: LIMITS_URL in r.url and r.request.method == "POST", timeout=15000):
            row.query_selector(".ai-limit-save").click()
        page.wait_for_timeout(500)
        updated = next((u for u in (page.evaluate(_GET, LIMITS_URL) or {}).get("users", []) if u["id"] == uid), {})
        _step(reporter, shots, page, "Per-user token limit override saves via UI",
              str(updated.get("limit_override")) == "50" and updated.get("effective_limit") == 50,
              f"user={uid} override={updated.get('limit_override')!r} effective={updated.get('effective_limit')!r}", "ai_limits_override")
        page.evaluate(_POST, [LIMITS_URL, {"user_id": uid, "limit": orig_row.get("limit_override", "")}])
    finally:
        page.evaluate(_POST, [LIMITS_URL, {"default_limit": original_default}])


def _layout_and_bulk(context, reporter, shots, snapshot):
    page = context.page
    layout = page.evaluate("""() => {
        const card = document.getElementById('aiUserLimitsCard'), ref = document.getElementById('aiSaveBtn');
        const cls = (el) => [...el.classList].filter(c => c !== 'ai-limit-save').sort().join(' ');
        return {above: !!(card.compareDocumentPosition(document.getElementById('aiPlatformModelList')) & Node.DOCUMENT_POSITION_FOLLOWING),
                framedTitle: !!card.querySelector('.input-group-text'),
                inputWidth: document.getElementById('aiDefaultLimitInput').getBoundingClientRect().width,
                sameSave: cls(document.getElementById('aiDefaultLimitSave')) === cls(ref) && (!card.querySelector('.ai-limit-save') || cls(card.querySelector('.ai-limit-save')) === cls(ref))};
    }""")
    ok = layout["above"] and not layout["framedTitle"] and layout["inputWidth"] >= 200 and layout["sameSave"]
    _step(reporter, shots, page, "Token-limit frame layout (above platform card, title label, wide input, app Save buttons)", ok, str(layout), "ai_limits_layout")

    rows = page.locator("#aiLimitsBody tr[data-user-id]").count()
    if rows:
        name = page.locator("#aiLimitsBody tr[data-user-id] td:nth-child(2)").first.inner_text().strip()
        page.fill("#aiLimitsSearch", name)
        found = page.locator("#aiLimitsBody tr[data-user-id]").count()
        page.fill("#aiLimitsSearch", "zz-no-such-user-zz")
        none = "No users match" in page.inner_text("#aiLimitsBody")
        page.fill("#aiLimitsSearch", "")
        _step(reporter, shots, page, "Token-limit search narrows and restores the user list", found >= 1 and none and
              page.locator("#aiLimitsBody tr[data-user-id]").count() == rows, f"match={found} none_msg={none} rows={rows}", "ai_limits_search")

    users = (snapshot or {}).get("users", [])
    eligible = [u for u in users if u["use_general"]]
    if not eligible:
        reporter.add_step("Toggle Select All + bulk apply", "Settings", "SKIP", "No user on general settings in this environment.")
        return
    try:
        page.click("#aiLimitsToggleAll")
        selected = page.inner_text("#aiLimitsSelectedCount")
        page.fill("#aiLimitsBulkValue", "321")
        with page.expect_response(lambda r: LIMITS_URL in r.url and r.request.method == "POST", timeout=15000):
            page.click("#aiLimitsBulkApply")
        page.wait_for_timeout(600)
        now = {u["id"]: u for u in (page.evaluate(_GET, LIMITS_URL + "?page_size=200") or {}).get("users", [])}
        applied = all(str(now[u["id"]]["limit_override"]) == "321" for u in eligible if u["id"] in now)
        _step(reporter, shots, page, "Toggle Select All + bulk apply sets the limit for every eligible user",
              applied and str(len(eligible)) in selected, f"selected={selected!r} eligible={len(eligible)} applied={applied}", "ai_limits_bulk")
    finally:
        for u in eligible:   # restore each user's original override
            page.evaluate(_POST, [LIMITS_URL, {"user_id": u["id"], "limit": u.get("limit_override", "")}])

    page.evaluate(_POST, [LIMITS_URL, {"default_limit": (snapshot or {}).get("default_limit", "0")}])
    toggle = page.query_selector("#aiLimitsTableHost .wf-table-toggle-btn")
    if rows > 5:
        _step(reporter, shots, page, "Token-limit table uses the shared Show all / Show less toggle", toggle is not None,
              f"rows={rows} toggle={'present' if toggle else 'missing'}", "ai_limits_collapse")
    else:
        reporter.add_step("Token-limit table Show all / Show less toggle", "Settings", "SKIP", f"Only {rows} users (needs more than 5).")


def test_ai_user_settings(context, reporter, screenshot_logger):
    close_global_modal(context.page)
    for phase in (_my_settings, _limits):
        try:
            phase(context, reporter, screenshot_logger)
        except Exception as ex:
            shot = screenshot_logger.capture(context.page, "settings", "ai_user_settings_error", "none", "fail", "fail")
            reporter.add_step(f"AI user settings ({phase.__name__})", "Settings", "FAIL", f"Exception: {ex}", screenshot_path=shot)
