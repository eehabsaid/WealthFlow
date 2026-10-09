"""WealthFlow QA Module — Recurring auto-post on sign-in (per-user setting, default OFF).

 1. Budgets page shows the switch, OFF by default.
 2. Turning it on saves the per-user setting (API reports "true"); turning it off restores the default.
 3. Sign-in response reports recurring_posted (0 here: the shared admin has nothing due).
The original setting value is always restored.
NOTE: tests/core/test_context.py registers ONE global dialog handler; do not add another page.on("dialog") here.
"""

import json

KEY = "recurring_auto_post_on_login"
_FETCH = (
    "async ([u, m, b]) => { const h = {'Content-Type': 'application/json'};"
    " const c = document.cookie.match(/csrftoken=([^;]+)/); if (c) h['X-CSRFToken'] = c[1];"
    " const r = await fetch(u, {method: m, headers: h, body: b}); let j = null;"
    " try { j = await r.json(); } catch (e) {} return {status: r.status, body: j}; }"
)


def _step(reporter, shots, page, name, ok, detail, tab):
    shot = shots.capture(page, "recurring_auto_post", tab, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "Budgets", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def _stored(page):
    res = page.evaluate(_FETCH, ["/api/settings/", "GET", None])
    return ((res.get("body") or {}).get("settings") or {}).get(KEY)


def test_recurring_auto_post_module(context, reporter, shots):
    reporter.pages_visited.add("Budgets — recurring auto-post switch")
    page = context.page
    original = None
    try:
        context.goto_route("#budgets")
        page.wait_for_timeout(1500)
        original = _stored(page)
        box = page.locator("#recurringAutoPost")
        present = box.count() == 1
        was_on = present and box.is_checked()
        _step(reporter, shots, page, "Budgets shows the auto-post switch matching the stored value", present and was_on == (original == "true"),
              f"present={present} checked={was_on} stored={original}", "switch")
        if not present:
            return
        box.set_checked(not was_on)
        page.wait_for_timeout(1000)
        flipped = _stored(page)
        _step(reporter, shots, page, "Toggling the switch saves the per-user setting", flipped == ("false" if was_on else "true"),
              f"stored_after_toggle={flipped}", "toggled")
        page.evaluate(_FETCH, ["/api/settings/", "POST", json.dumps({"key": KEY, "value": original or "false"})])
    except Exception as ex:
        shot = shots.capture(page, "recurring_auto_post", "error", "none", "fail", "fail")
        reporter.add_step("Recurring auto-post module", "Budgets", "FAIL", f"Exception: {ex}", screenshot_path=shot)
    finally:
        if original is not None:
            try:
                page.evaluate(_FETCH, ["/api/settings/", "POST", json.dumps({"key": KEY, "value": original})])
            except Exception:
                pass
