"""Balance module phase 5: Credit Card Payment CRUD. Split out of tests/modules/balance.py."""

from tests.core.crud_verifier import CrudVerifier


def test_credit_card_payment(context, reporter, screenshot_logger):
    # 5. Credit Card Payment — real, API-verified. Also requires a bank to
    # pay from; same skip-if-no-prerequisite-data convention as above.
    ccp_checker = CrudVerifier(context.page, api_list_url="/api/credit-card-payments/", list_key="credit_card_payments")
    try:
        context.goto_route("#balance")
        context.page.evaluate("if (typeof switchTab === 'function') switchTab('credit_card_payment');")
        context.page.wait_for_timeout(500)

        before_ids = ccp_checker.snapshot_ids()

        context.page.evaluate("if (typeof showCreditCardPaymentModal === 'function') showCreditCardPaymentModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Credit Card Payment Modal")
        shot_ccp = screenshot_logger.capture(context.page, "balance", "credit_card_payment_modal", "showCreditCardPaymentModal", "open", "ok")
        ccp_checker.add_manual_step(context.page.query_selector("#creditCardPaymentForm") is not None)

        bank_options = context.page.evaluate("(() => { const el = document.getElementById('ccp_bank'); return el ? el.options.length : 0; })()")
        filled = False
        ccp_amount = "60.00"
        if bank_options and bank_options > 1:
            context.page.select_option("#ccp_bank", index=1)
            if context.page.query_selector("#ccp_amount"):
                context.page.fill("#ccp_amount", ccp_amount)
                filled = True
            save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
            if save_btn and filled:
                save_btn.click()
                context.page.wait_for_timeout(800)
        else:
            context.page.evaluate("if (typeof closeModal === 'function') closeModal();")

        ccp_checker.add_manual_step(filled)

        if filled:
            create_result = ccp_checker.verify_created(before_ids, match_field="amount_egp", expected_value=ccp_amount)
            new_id = create_result.new_id

            if new_id is not None:
                context.page.evaluate(f"if (typeof showCreditCardPaymentModal === 'function') showCreditCardPaymentModal({new_id});")
                context.page.wait_for_timeout(600)
                new_amount = "80.00"
                if context.page.query_selector("#ccp_amount"):
                    context.page.fill("#ccp_amount", new_amount)
                    save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
                    if save_btn:
                        save_btn.click()
                        context.page.wait_for_timeout(800)
                context.page.evaluate("if (typeof closeModal === 'function') closeModal();")
                edit_result = ccp_checker.verify_field_updated(new_id, "amount_egp", new_amount)

                context.page.evaluate(f"(async () => {{ if (typeof deleteCreditCardPayment === 'function') {{ await deleteCreditCardPayment({new_id}); }} }})()")
                context.page.wait_for_timeout(1200)
                delete_result = ccp_checker.verify_deleted(new_id)

                overall_pass = create_result.passed and edit_result.passed and delete_result.passed
                detail = f"Create: {create_result.detail} | Edit: {edit_result.detail} | Delete: {delete_result.detail}"
                status = "PASS" if overall_pass else "FAIL"
            else:
                detail = create_result.detail
                status = "FAIL"
        else:
            detail = "Skipped real save: no bank accounts exist yet to pay from (needs prerequisite data)."
            status = "SKIP"

        reporter.record_crud("Credit Card Payment Entry", ccp_checker.steps_passed, max(ccp_checker.steps_total, 1))
        reporter.add_step("Credit Card Payment CRUD (API-verified)", "Balance & Net Worth", status, detail, screenshot_path=shot_ccp)
    except Exception as ex:
        reporter.record_crud("Credit Card Payment Entry", ccp_checker.steps_passed, max(ccp_checker.steps_total, 1))
        reporter.add_step("Credit Card Payment Modal Test", "Balance & Net Worth", "FAIL", f"Exception: {ex}")

