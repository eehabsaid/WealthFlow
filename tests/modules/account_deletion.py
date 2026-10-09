"""WealthFlow QA Module — Account deletion with grace period (soft-delete, restore, last-admin protection).

Uses a throw-away user created through the admin API (removed again at the end), never a real account:
 1. Admin Users screen: delete schedules the deletion; the row shows Restore + Delete-permanently and the purge date.
 2. Restore from the row brings the account back (trash button returns).
 3. A scheduled user cannot sign in: the login page says so and offers 'Restore my account'.
 4. The restore page rejects a wrong password and, with the right one, restores; the user can sign in again.
 The last-active-admin refusal is covered by Django tests only: this module never deletes the signed-in account.
NOTE: tests/core/test_context.py registers ONE global dialog handler (accepts confirm()); do not add another.
"""

from tests.core.test_context import TestContext

BASE = "http://127.0.0.1:8000"
USER, PASSWORD = "e2e_grace_probe", "SecurePass123!"
_FETCH = (
    "async ([u, m, b]) => { const h = {'Content-Type': 'application/json'};"
    " const c = document.cookie.match(/csrftoken=([^;]+)/); if (c) h['X-CSRFToken'] = c[1];"
    " const r = await fetch(u, {method: m, headers: h, body: b}); let j = null;"
    " try { j = await r.json(); } catch (e) {} return {status: r.status, body: j}; }"
)


def _step(reporter, shots, page, name, ok, detail, tab):
    shot = shots.capture(page, "account_deletion", tab, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "Account deletion", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def _api(page, url, method="GET", body=None):
    import json
    return page.evaluate(_FETCH, [url, method, json.dumps(body) if body is not None else None])


def _purge_leftover(page):
    """Remove a probe user left behind by an interrupted earlier run."""
    rows = (_api(page, "/api/users/").get("body") or {}).get("users", [])
    for row in rows:
        if row.get("username") == USER:
            _api(page, f"/api/users/{row['id']}/", "DELETE")
            _api(page, f"/api/users/{row['id']}/?purge_now=1", "DELETE")


def _open_users(context):
    context.goto_route("#settings")
    context.page.wait_for_timeout(1000)
    context.page.evaluate("() => { if (window.renderUserSettings) window.renderUserSettings(); }")
    context.page.wait_for_timeout(1200)


def _row_actions(page, uid):
    return {k: page.locator(f"[data-user-{k}='{uid}']").count() for k in ("delete", "restore", "purge")}


def _check_admin_screen(context, reporter, shots, uid):
    page = context.page
    _open_users(context)
    before = _row_actions(page, uid)
    page.click(f"[data-user-delete='{uid}']")
    page.wait_for_timeout(1500)
    after = _row_actions(page, uid)
    stamp = page.locator(f"[data-user-purge-at='{uid}']").count()
    _step(reporter, shots, page, "Admin delete schedules deletion (Restore + permanent delete shown with purge date)",
          before["delete"] == 1 and after["restore"] == 1 and after["purge"] == 1 and after["delete"] == 0 and stamp == 1,
          f"before={before} after={after} purge_date_shown={stamp}", "users_pending")
    page.click(f"[data-user-restore='{uid}']")
    page.wait_for_timeout(1500)
    back = _row_actions(page, uid)
    _step(reporter, shots, page, "Restore from the Users row re-enables the account", back["delete"] == 1 and back["restore"] == 0,
          f"after_restore={back}", "users_restored")
    _api(page, f"/api/users/{uid}/", "DELETE")


def _check_public_flow(context, reporter, shots):
    ctx = TestContext(context.playwright, headed=context.headed, slow_mo=context.slow_mo, device="desktop", theme=context.theme)
    try:
        page = ctx.page
        page.goto(f"{BASE}/accounts/login/")
        page.fill("input[name='username']", USER)
        page.fill("input[name='password']", PASSWORD)
        page.click("button[type='submit']")
        page.wait_for_timeout(1500)
        link = page.locator("#restoreAccountLink").count()
        _step(reporter, shots, page, "Scheduled user cannot sign in: clear message and restore link", link == 1 and "/accounts/login" in page.url,
              f"restore_link={link} url={page.url}", "login_blocked")
        page.click("#restoreAccountLink")
        page.wait_for_timeout(1000)
        forgot = page.locator("#restoreForgotLink").count()
        _step(reporter, shots, page, "Restore page offers Forgot Password so users can help themselves", forgot == 1, f"forgot_link={forgot}", "restore_forgot")
        page.fill("#restorePasswordInput", "wrong-password")
        page.click("#restoreForm button[type='submit']")
        page.wait_for_timeout(1200)
        still = page.locator(".alert-dark-danger").count() == 1
        _step(reporter, shots, page, "Restore page rejects a wrong password", still, f"error_shown={still}", "restore_wrong")
        page.fill("#restorePasswordInput", PASSWORD)
        page.click("#restoreForm button[type='submit']")
        page.wait_for_timeout(1500)
        done = page.locator(".alert-dark-success, [data-i18n='auth_restore_done']").count() >= 1
        _step(reporter, shots, page, "Restore page restores the account with the right password", done, f"success_shown={done}", "restore_ok")
        page.goto(f"{BASE}/accounts/login/")
        page.fill("input[name='username']", USER)
        page.fill("input[name='password']", PASSWORD)
        page.click("button[type='submit']")
        page.wait_for_timeout(2000)
        _step(reporter, shots, page, "Restored user can sign in again", "/accounts/login" not in page.url, f"url={page.url}", "login_after_restore")
    finally:
        try:
            ctx.browser.close()
        except Exception:
            pass


def test_account_deletion_module(context, reporter, shots):
    reporter.pages_visited.add("Account deletion — grace period / restore")
    page = context.page
    uid = None
    try:
        context.goto_route("#dashboard")
        page.wait_for_timeout(800)
        _purge_leftover(page)
        made = _api(page, "/api/users/", "POST", {"username": USER, "email": f"{USER}@example.com", "password": PASSWORD})
        uid = ((made.get("body") or {}).get("user") or {}).get("id")
        _step(reporter, shots, page, "Probe user created for the deletion flow", bool(uid), f"status={made['status']}", "probe_user")
        if not uid:
            return
        _check_admin_screen(context, reporter, shots, uid)
        _api(page, f"/api/users/{uid}/", "DELETE")  # schedule again for the public restore flow
        _check_public_flow(context, reporter, shots)
    except Exception as ex:
        shot = shots.capture(page, "account_deletion", "error", "none", "fail", "fail")
        reporter.add_step("Account deletion module", "Account deletion", "FAIL", f"Exception: {ex}", screenshot_path=shot)
    finally:
        if uid:
            try:
                _api(page, f"/api/users/{uid}/", "DELETE")
                _api(page, f"/api/users/{uid}/?purge_now=1", "DELETE")
            except Exception:
                pass
