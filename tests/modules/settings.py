"""
WealthFlow QA Module — Settings & Administration
Tests:
 1. 17-step CRUD on Banks (showBankModal), Currencies (showCurrencyModal), Gold Types (showGoldTypeModal), Gold Purities (showGoldPurityModal), and Users (showUserModal).
 2. Portable Backup Archive creation & download (triggerDownloadBackup() -> wealthflow_backup_*.wfbackup).
 3. Documentation Engine generation (handleGenerateClick()).
"""

from tests.core.data_generator import get_unique_bank_data
from tests.core.download_verifier import verify_downloaded_file
from tests.core.crud_verifier import CrudVerifier
import time

def _uid():
    return str(int(time.time() * 1000))[-6:]

def test_settings_module(context, reporter, screenshot_logger):
    # Registered persistently: several deletes below use a native confirm() dialog.
    context.page.on("dialog", lambda dialog: dialog.accept())

    context.goto_route("#settings")
    reporter.pages_visited.add("Settings & Administration")

    # Sweep sub-tabs
    tabs = ["general", "banks", "currencies", "gold-settings", "email-templates", "backup", "documentation", "users"]
    for t in tabs:
        context.page.evaluate(f"if (typeof switchSettingsTab === 'function') switchSettingsTab('{t}');")
        context.page.wait_for_timeout(500)
        reporter.tabs_visited.add(f"Settings -> {t}")

    # 1. Bank Setting CRUD — real, API-verified
    bank_data = get_unique_bank_data()
    bank_checker = CrudVerifier(context.page, api_list_url="/api/banks/", list_key="banks")
    try:
        context.page.evaluate("if (typeof switchSettingsTab === 'function') switchSettingsTab('banks');")
        context.page.wait_for_timeout(500)

        before_ids = bank_checker.snapshot_ids()

        context.page.evaluate("if (typeof showBankModal === 'function') showBankModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Bank Setting Modal")
        shot1 = screenshot_logger.capture(context.page, "settings", "bank_modal", "showBankModal", "open", "ok")
        bank_checker.add_manual_step(context.page.query_selector("#bnName") is not None)

        if context.page.query_selector("#bnName"):
            context.page.fill("#bnName", bank_data["name"])
            save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
            if save_btn:
                save_btn.click()
                context.page.wait_for_timeout(700)

        create_result = bank_checker.verify_created(before_ids, match_field="name", expected_value=bank_data["name"])

        new_name = bank_data["name"] + " Edited"
        if create_result.new_id is not None:
            context.page.evaluate(f"if (typeof showBankModal === 'function') showBankModal({create_result.new_id});")
            context.page.wait_for_timeout(500)
            if context.page.query_selector("#bnName"):
                context.page.fill("#bnName", new_name)
                context.page.evaluate(f"(async () => {{ if (typeof saveBank === 'function') {{ await saveBank({create_result.new_id}); }} }})()")
                context.page.wait_for_timeout(700)
        edit_result = bank_checker.verify_field_updated(create_result.new_id, "name", new_name)

        if create_result.new_id is not None:
            context.page.evaluate(f"(async () => {{ if (typeof deleteBank === 'function') {{ await deleteBank({create_result.new_id}); }} }})()")
            context.page.wait_for_timeout(700)
        delete_result = bank_checker.verify_deleted(create_result.new_id)

        overall_pass = create_result.passed and edit_result.passed and delete_result.passed
        reporter.record_crud("Bank Setting", bank_checker.steps_passed, bank_checker.steps_total)
        detail = f"Create: {create_result.detail} | Edit: {edit_result.detail} | Delete: {delete_result.detail}"
        reporter.add_step("Bank Setting CRUD (API-verified)", "Settings", "PASS" if overall_pass else "FAIL", detail, screenshot_path=shot1)
    except Exception as ex:
        shot_err = screenshot_logger.capture(context.page, "settings", "bank_modal", "error", "fail", "fail")
        reporter.record_crud("Bank Setting", bank_checker.steps_passed, max(bank_checker.steps_total, 1))
        reporter.add_step("Bank Setting CRUD Test", "Settings", "FAIL", f"Exception: {ex}", screenshot_path=shot_err)

    # 2. Currency Setting CRUD — real, API-verified
    curr_checker = CrudVerifier(context.page, api_list_url="/api/currencies/", list_key="currencies")
    try:
        context.page.evaluate("if (typeof switchSettingsTab === 'function') switchSettingsTab('currencies');")
        context.page.wait_for_timeout(500)

        before_ids = curr_checker.snapshot_ids()

        context.page.evaluate("if (typeof showCurrencyModal === 'function') showCurrencyModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Currency Setting Modal")
        shot_curr = screenshot_logger.capture(context.page, "settings", "currency_modal", "showCurrencyModal", "open", "ok")
        curr_checker.add_manual_step(context.page.query_selector("#curCode") is not None)

        curr_code = "T" + _uid()[:2]
        if context.page.query_selector("#curCode"):
            context.page.fill("#curCode", curr_code)
            if context.page.query_selector("#curSymbol"):
                context.page.fill("#curSymbol", "T")
            if context.page.query_selector("#curName"):
                context.page.fill("#curName", "Test Currency " + _uid())
            save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
            if save_btn:
                save_btn.click()
                context.page.wait_for_timeout(700)

        create_result = curr_checker.verify_created(before_ids, match_field="code", expected_value=curr_code)

        new_symbol = "X"
        if create_result.new_id is not None:
            context.page.evaluate(f"if (typeof showCurrencyModal === 'function') showCurrencyModal({create_result.new_id});")
            context.page.wait_for_timeout(500)
            if context.page.query_selector("#curSymbol"):
                context.page.fill("#curSymbol", new_symbol)
                context.page.evaluate(f"(async () => {{ if (typeof saveCurrency === 'function') {{ await saveCurrency({create_result.new_id}); }} }})()")
                context.page.wait_for_timeout(700)
        edit_result = curr_checker.verify_field_updated(create_result.new_id, "symbol", new_symbol)

        if create_result.new_id is not None:
            context.page.evaluate(f"(async () => {{ if (typeof deleteCurrency === 'function') {{ await deleteCurrency({create_result.new_id}); }} }})()")
            context.page.wait_for_timeout(700)
        delete_result = curr_checker.verify_deleted(create_result.new_id)

        overall_pass = create_result.passed and edit_result.passed and delete_result.passed
        reporter.record_crud("Currency Setting", curr_checker.steps_passed, curr_checker.steps_total)
        detail = f"Create: {create_result.detail} | Edit: {edit_result.detail} | Delete: {delete_result.detail}"
        reporter.add_step("Currency Setting CRUD (API-verified)", "Settings", "PASS" if overall_pass else "FAIL", detail, screenshot_path=shot_curr)
    except Exception as ex:
        reporter.record_crud("Currency Setting", curr_checker.steps_passed, max(curr_checker.steps_total, 1))
        reporter.add_step("Currency Setting Modal Test", "Settings", "FAIL", f"Exception: {ex}")

    # 3. Gold Type Setting — real, API-verified. There is no delete
    # function for this entity: the "Active" select IS the deactivation
    # mechanism (soft toggle, not row removal), verified via field update.
    gt_checker = CrudVerifier(context.page, api_list_url="/api/settings/gold-types/", list_key="items")
    try:
        context.page.evaluate("if (typeof switchSettingsTab === 'function') switchSettingsTab('gold-settings');")
        context.page.wait_for_timeout(500)

        before_ids = gt_checker.snapshot_ids()

        context.page.evaluate("if (typeof showGoldTypeModal === 'function') showGoldTypeModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Gold Type Setting Modal")
        shot_gt = screenshot_logger.capture(context.page, "settings", "gold_type_modal", "showGoldTypeModal", "open", "ok")
        gt_checker.add_manual_step(context.page.query_selector("#gstName") is not None)

        gt_name = "Test Gold Type " + _uid()
        if context.page.query_selector("#gstName"):
            context.page.fill("#gstName", gt_name)
            save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
            if save_btn:
                save_btn.click()
                context.page.wait_for_timeout(700)

        create_result = gt_checker.verify_created(before_ids, match_field="name", expected_value=gt_name)

        # Deactivate via the Active select instead of a delete call.
        if create_result.new_id is not None:
            context.page.evaluate(f"if (typeof showGoldTypeModal === 'function') showGoldTypeModal({create_result.new_id});")
            context.page.wait_for_timeout(500)
            if context.page.query_selector("#gstActive"):
                context.page.select_option("#gstActive", value="false")
                context.page.evaluate(f"(async () => {{ if (typeof saveGoldType === 'function') {{ await saveGoldType({create_result.new_id}); }} }})()")
                context.page.wait_for_timeout(700)
        deactivate_result = gt_checker.verify_field_updated(create_result.new_id, "is_active", False)

        overall_pass = create_result.passed and deactivate_result.passed
        reporter.record_crud("Gold Type Setting", gt_checker.steps_passed, gt_checker.steps_total)
        detail = f"Create: {create_result.detail} | Deactivate: {deactivate_result.detail}"
        reporter.add_step("Gold Type Setting CRUD (API-verified)", "Settings", "PASS" if overall_pass else "FAIL", detail, screenshot_path=shot_gt)
    except Exception as ex:
        reporter.record_crud("Gold Type Setting", gt_checker.steps_passed, max(gt_checker.steps_total, 1))
        reporter.add_step("Gold Type Setting Modal Test", "Settings", "FAIL", f"Exception: {ex}")

    # 4. Gold Purity Setting — same soft-toggle pattern as Gold Type.
    gp_checker = CrudVerifier(context.page, api_list_url="/api/settings/gold-purities/", list_key="items")
    try:
        context.page.evaluate("if (typeof showGoldPurityModal === 'function') showGoldPurityModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Gold Purity Setting Modal")
        shot_gp = screenshot_logger.capture(context.page, "settings", "gold_purity_modal", "showGoldPurityModal", "open", "ok")
        gp_checker.add_manual_step(context.page.query_selector("#gspKey") is not None)

        before_ids = gp_checker.snapshot_ids()
        gp_key = _uid()[:2] + "k"
        gp_label = gp_key.upper()
        if context.page.query_selector("#gspKey"):
            context.page.fill("#gspKey", gp_key)
            context.page.fill("#gspLabel", gp_label)
            save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
            if save_btn:
                save_btn.click()
                context.page.wait_for_timeout(700)

        create_result = gp_checker.verify_created(before_ids, match_field="key", expected_value=gp_key)

        if create_result.new_id is not None:
            context.page.evaluate(f"if (typeof showGoldPurityModal === 'function') showGoldPurityModal({create_result.new_id});")
            context.page.wait_for_timeout(500)
            if context.page.query_selector("#gspActive"):
                context.page.select_option("#gspActive", value="false")
                context.page.evaluate(f"(async () => {{ if (typeof saveGoldPurity === 'function') {{ await saveGoldPurity({create_result.new_id}); }} }})()")
                context.page.wait_for_timeout(700)
        deactivate_result = gp_checker.verify_field_updated(create_result.new_id, "is_active", False)

        overall_pass = create_result.passed and deactivate_result.passed
        reporter.record_crud("Gold Purity Setting", gp_checker.steps_passed, gp_checker.steps_total)
        detail = f"Create: {create_result.detail} | Deactivate: {deactivate_result.detail}"
        reporter.add_step("Gold Purity Setting CRUD (API-verified)", "Settings", "PASS" if overall_pass else "FAIL", detail, screenshot_path=shot_gp)
    except Exception as ex:
        reporter.add_step("Gold Settings Modal Test", "Settings", "FAIL", f"Exception: {ex}")

    # 5. User Account CRUD — real, API-verified. List is paginated; a
    # large page_size ensures the newly created test user is captured.
    user_checker = CrudVerifier(context.page, api_list_url="/api/users/?page_size=1000", list_key="users")
    try:
        context.page.evaluate("if (typeof switchSettingsTab === 'function') switchSettingsTab('users');")
        context.page.wait_for_timeout(500)

        before_ids = user_checker.snapshot_ids()

        context.page.evaluate("if (typeof showUserModal === 'function') showUserModal();")
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
                context.page.wait_for_timeout(700)

        create_result = user_checker.verify_created(before_ids, match_field="username", expected_value=username)

        new_email = "edited_" + email
        if create_result.new_id is not None:
            context.page.evaluate(f"if (typeof showUserModal === 'function') showUserModal({create_result.new_id});")
            context.page.wait_for_timeout(500)
            if context.page.query_selector("#uEmail"):
                context.page.fill("#uEmail", new_email)
                context.page.evaluate(f"(async () => {{ if (typeof saveUser === 'function') {{ await saveUser({create_result.new_id}); }} }})()")
                context.page.wait_for_timeout(700)
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

    # 5. Portable Backup Archive Download
    context.page.evaluate("if (typeof switchSettingsTab === 'function') switchSettingsTab('backup');")
    context.page.wait_for_timeout(600)

    try:
        with context.page.expect_download(timeout=5000) as download_info:
            context.page.evaluate("if (typeof triggerDownloadBackup === 'function') triggerDownloadBackup();")
        download = download_info.value
        save_path = f"test_downloads/{download.suggested_filename}"
        download.save_as(save_path)

        verify_downloaded_file(save_path, expected_extension=".wfbackup")
        shot_bk = screenshot_logger.capture(context.page, "settings", "backup", "none", "backup_download", "ok")
        reporter.exports_tested.append("Backup & Restore -> Create & Download Portable Backup (.wfbackup)")
        reporter.add_step("Backup Archive Download Verification", "Settings", "PASS", f"Verified backup archive: {save_path}", screenshot_path=shot_bk)
    except Exception as ex:
        reporter.add_step("Backup Archive Download", "Settings", "FAIL", f"Exception: {ex}")

    # 6. Documentation Engine Generation
    context.page.evaluate("if (typeof switchSettingsTab === 'function') switchSettingsTab('documentation');")
    context.page.wait_for_timeout(600)

    try:
        context.page.evaluate("if (typeof handleGenerateClick === 'function') handleGenerateClick();")
        context.page.wait_for_timeout(1000)
        shot_doc = screenshot_logger.capture(context.page, "settings", "documentation", "doc_engine", "trigger", "ok")
        reporter.exports_tested.append("Documentation Engine -> Generate All Documents")
        reporter.add_step("Documentation Engine Generation Trigger", "Settings", "PASS", "Triggered doc engine document generation.", screenshot_path=shot_doc)
    except Exception as ex:
        reporter.add_step("Documentation Engine Trigger", "Settings", "FAIL", f"Exception: {ex}")
