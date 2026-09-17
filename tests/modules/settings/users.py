"""Settings module phase 5: User Account CRUD. Split out of tests/modules/settings.py."""

from tests.core.crud_verifier import CrudVerifier
from tests.modules.settings.common import _uid


def test_users(context, reporter, screenshot_logger):
    # 5. User Account CRUD — real, API-verified. List is paginated; a
    # large page_size ensures the newly created test user is captured.
    user_checker = CrudVerifier(context.page, api_list_url="/api/users/?page_size=1000", list_key="users")
    try:
        context.page.evaluate("if (typeof switchSettingsTab === 'function') switchSettingsTab('users'); else if (typeof navigate === 'function') navigate('settings-users');")
        context.page.wait_for_timeout(500)

        before_ids = user_checker.snapshot_ids()

        context.page.evaluate("(async () => { if (typeof showUserModal === 'function') await showUserModal(); })()")
        try:
            context.page.wait_for_selector("#globalModal.show #uName", state="visible", timeout=6000)
        except Exception:
            context.page.wait_for_timeout(600)
        reporter.modals_opened.add("User Management Modal")
        shot_usr = screenshot_logger.capture(context.page, "settings", "user_modal", "showUserModal", "open", "ok")
        user_checker.add_manual_step(context.page.query_selector("#uName") is not None)

        username = "e2e_test_" + _uid()
        email = f"{username}@example.test"
        if context.page.query_selector("#uName"):
            context.page.fill("#uName", username)
            context.page.fill("#uEmail", email)
            if context.page.query_selector("#uPassword"):
                context.page.fill("#uPassword", "TestPass123!")
            save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
            if save_btn:
                save_btn.click()
                try:
                    context.page.wait_for_selector("#globalModal.show", state="hidden", timeout=8000)
                except Exception:
                    pass
                context.page.wait_for_timeout(500)

        create_result = user_checker.verify_created(before_ids, match_field="username", expected_value=username)

        new_email = "edited_" + email
        if create_result.new_id is not None:
            context.page.evaluate(f"(async () => {{ if (typeof showUserModal === 'function') await showUserModal({create_result.new_id}); }})()")
            try:
                context.page.wait_for_selector("#globalModal.show #uEmail", state="visible", timeout=8000)
            except Exception:
                context.page.wait_for_timeout(600)
            if context.page.query_selector("#globalModal.show #uEmail"):
                context.page.fill("#globalModal.show #uEmail", new_email)
                context.page.evaluate(f"(async () => {{ if (typeof saveUser === 'function') {{ await saveUser({create_result.new_id}); }} }})()")
                try:
                    context.page.wait_for_selector("#globalModal.show", state="hidden", timeout=8000)
                except Exception:
                    pass
                context.page.wait_for_timeout(500)
        edit_result = user_checker.verify_field_updated(create_result.new_id, "email", new_email)

        if create_result.new_id is not None:
            context.page.evaluate(f"(async () => {{ if (typeof deleteUser === 'function') {{ await deleteUser({create_result.new_id}); }} }})()")
            context.page.wait_for_timeout(700)
        delete_result = user_checker.verify_deleted(create_result.new_id)

        overall_pass = create_result.passed and edit_result.passed and delete_result.passed
        reporter.record_crud("User Account Entry", user_checker.steps_passed, user_checker.steps_total)
        detail = f"Create: {create_result.detail} | Edit: {edit_result.detail} | Delete: {delete_result.detail}"
        reporter.add_step("User Management CRUD (API-verified)", "Settings", "PASS" if overall_pass else "FAIL", detail, screenshot_path=shot_usr)
    except Exception as ex:
        reporter.record_crud("User Account Entry", user_checker.steps_passed, max(user_checker.steps_total, 1))
        reporter.add_step("User Management Modal Test", "Settings", "FAIL", f"Exception: {ex}")

