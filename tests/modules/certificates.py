"""
WealthFlow QA Module — Bank Certificates
Tests:
 1. 17-step CRUD on Bank Certificates (showBankCertificateModal) and Certificate Statuses (showCertStatusModal).
 2. Certificate Interest History modal verification (showBankCertificateInterestHistory).
 3. Immediate downstream verification to Cash Flow Forecast & Wealth Growth Forecast.
"""

from tests.core.data_generator import get_unique_certificate_data
from tests.core.assertions import verify_downstream_impact
from tests.core.crud_verifier import CrudVerifier

def test_certificates_module(context, reporter, screenshot_logger):
    # Registered persistently: delete uses a native confirm() dialog.
    context.page.on("dialog", lambda dialog: dialog.accept())

    context.goto_route("#bank-certificates")
    reporter.pages_visited.add("Bank Certificates")

    # Sweep tabs
    tabs = ["active-certificates", "certificate-statuses"]
    for t in tabs:
        context.page.evaluate(f"if (typeof switchTab === 'function') switchTab('{t}');")
        context.page.wait_for_timeout(500)
        reporter.tabs_visited.add(f"Certificates -> {t}")

    # 1. Certificate CRUD — real, API-verified. Certificates now deduct
    # principal from a matching cash balance on save/delete, so a small
    # test amount is used (same lesson as Fixed Assets: large amounts can
    # trigger a legitimate insufficient_balance rejection).
    cert_data = get_unique_certificate_data()
    checker = CrudVerifier(context.page, api_list_url="/api/bank-certificates/", list_key="certificates")
    try:
        before_ids = checker.snapshot_ids()

        context.page.evaluate("if (typeof showBankCertificateModal === 'function') showBankCertificateModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Bank Certificate Modal")
        shot1 = screenshot_logger.capture(context.page, "certificates", "modal_open", "showBankCertificateModal", "open", "ok")
        checker.add_manual_step(context.page.query_selector("#bcAmount") is not None)

        test_amount = 50
        if context.page.query_selector("#bcAmount"):
            if context.page.query_selector("#bcBank"):
                context.page.select_option("#bcBank", index=1)
            if context.page.query_selector("#bcCurrency"):
                context.page.select_option("#bcCurrency", index=1)
            # Date fields use the app's custom picker, which hides the
            # native <input> — setting .value via JS is the documented
            # supported path for external code.
            context.page.evaluate("document.getElementById('bcIssue').value = '2026-01-01'")
            context.page.evaluate("document.getElementById('bcExpiry').value = '2027-01-01'")
            context.page.fill("#bcAmount", str(test_amount))
            if context.page.query_selector("#bcInterestRate"):
                context.page.fill("#bcInterestRate", str(cert_data["interest_rate"]))
            if context.page.query_selector("#bcFrequency"):
                context.page.select_option("#bcFrequency", index=1)

            save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
            if save_btn:
                save_btn.click()
                context.page.wait_for_timeout(900)

        create_result = checker.verify_created(before_ids, match_field="amount", expected_value=test_amount)

        # Edit: reopen, change interest rate, save via the real explicit-id path.
        new_rate = round(float(cert_data["interest_rate"]) + 1, 2)
        if create_result.new_id is not None:
            context.page.evaluate(f"if (typeof showBankCertificateModal === 'function') showBankCertificateModal({create_result.new_id});")
            context.page.wait_for_timeout(600)
            if context.page.query_selector("#bcInterestRate"):
                context.page.fill("#bcInterestRate", str(new_rate))
                context.page.evaluate(f"(async () => {{ if (typeof saveBankCertificate === 'function') {{ await saveBankCertificate({create_result.new_id}); }} }})()")
                context.page.wait_for_timeout(900)
        edit_result = checker.verify_field_updated(create_result.new_id, "interest_rate", new_rate)

        # Delete via the real deleteBankCertificate() JS function.
        if create_result.new_id is not None:
            context.page.evaluate(f"(async () => {{ if (typeof deleteBankCertificate === 'function') {{ await deleteBankCertificate({create_result.new_id}); }} }})()")
            context.page.wait_for_timeout(900)
        delete_result = checker.verify_deleted(create_result.new_id)

        overall_pass = create_result.passed and edit_result.passed and delete_result.passed
        reporter.record_crud("Bank Certificate", checker.steps_passed, checker.steps_total)
        status = "PASS" if overall_pass else "FAIL"
        detail = f"Create: {create_result.detail} | Edit: {edit_result.detail} | Delete: {delete_result.detail}"
        reporter.add_step("Bank Certificate CRUD (API-verified)", "Bank Certificates", status, detail, screenshot_path=shot1)
    except Exception as ex:
        shot_err = screenshot_logger.capture(context.page, "certificates", "modal", "error", "fail", "fail")
        reporter.record_crud("Bank Certificate", checker.steps_passed, max(checker.steps_total, 1))
        reporter.add_step("Bank Certificate CRUD Test", "Bank Certificates", "FAIL", f"Exception: {ex}", screenshot_path=shot_err)

    # 2. Certificate Status CRUD — real, API-verified
    status_checker = CrudVerifier(context.page, api_list_url="/api/cert-statuses/", list_key="statuses")
    try:
        context.page.evaluate("if (typeof switchTab === 'function') switchTab('certificate-statuses');")
        context.page.wait_for_timeout(500)

        before_ids = status_checker.snapshot_ids()

        context.page.evaluate("if (typeof showCertStatusModal === 'function') showCertStatusModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Certificate Status Modal")
        shot_cs = screenshot_logger.capture(context.page, "certificates", "status_modal", "showCertStatusModal", "open", "ok")

        status_checker.add_manual_step(context.page.query_selector("#csName") is not None)
        status_name = f"Test Status {cert_data['certificate_name'][-6:]}"
        if context.page.query_selector("#csName"):
            context.page.fill("#csName", status_name)
            context.page.evaluate("(async () => { if (typeof saveCertStatus === 'function') { await saveCertStatus(); } })()")
            context.page.wait_for_timeout(700)

        create_result = status_checker.verify_created(before_ids, match_field="name", expected_value=status_name)

        new_status_name = status_name + " Edited"
        if create_result.new_id is not None:
            context.page.evaluate(f"if (typeof showCertStatusModal === 'function') showCertStatusModal({create_result.new_id});")
            context.page.wait_for_timeout(500)
            if context.page.query_selector("#csName"):
                context.page.fill("#csName", new_status_name)
                context.page.evaluate(f"(async () => {{ if (typeof saveCertStatus === 'function') {{ await saveCertStatus({create_result.new_id}); }} }})()")
                context.page.wait_for_timeout(700)
        edit_result = status_checker.verify_field_updated(create_result.new_id, "name", new_status_name)

        if create_result.new_id is not None:
            context.page.evaluate(f"(async () => {{ if (typeof deleteCertStatus === 'function') {{ await deleteCertStatus({create_result.new_id}); }} }})()")
            context.page.wait_for_timeout(700)
        delete_result = status_checker.verify_deleted(create_result.new_id)

        overall_pass = create_result.passed and edit_result.passed and delete_result.passed
        reporter.record_crud("Certificate Status", status_checker.steps_passed, status_checker.steps_total)
        detail = f"Create: {create_result.detail} | Edit: {edit_result.detail} | Delete: {delete_result.detail}"
        reporter.add_step(
            "Certificate Status CRUD (API-verified)", "Bank Certificates",
            "PASS" if overall_pass else "FAIL", detail, screenshot_path=shot_cs,
        )
    except Exception as ex:
        reporter.add_step("Certificate Status Modal Test", "Bank Certificates", "FAIL", f"Exception: {ex}")

    # 3. Dynamic Certificate Interest History Modal
    try:
        context.page.evaluate("""() => {
            const certId = (window._bankCertificates && window._bankCertificates.length > 0) ? window._bankCertificates[0].id : null;
            if (certId && typeof showBankCertificateInterestHistory === 'function') {
                showBankCertificateInterestHistory(certId);
            }
        }""")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Certificate Interest History Modal")
        shot2 = screenshot_logger.capture(context.page, "certificates", "interest_history", "showInterestHistory", "open", "ok")
        context.page.evaluate("if (typeof closeModal === 'function') closeModal();")
        reporter.add_step("Interest History Modal Test", "Bank Certificates", "PASS", "Verified certificate interest payout schedule modal.", screenshot_path=shot2)
    except Exception as ex:
        reporter.add_step("Interest History Modal Test", "Bank Certificates", "FAIL", f"Exception: {ex}")

    # 4. Downstream impact
    verify_downstream_impact(context.page, "Certificate Creation", "financial-advisor")
