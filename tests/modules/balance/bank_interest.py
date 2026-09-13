"""Balance module phase 4: Bank Interest CRUD. Split out of tests/modules/balance.py."""

from tests.core.crud_verifier import CrudVerifier


def test_bank_interest(context, reporter, screenshot_logger):
    # 4. Bank Interest — real, API-verified. Requires a bank to select from;
    # if none exist yet, the full create is skipped and only the modal's
    # structural presence is verified (same convention as Currency Exchange).
    interest_checker = CrudVerifier(context.page, api_list_url="/api/bank-interests/", list_key="bank_interests")
    try:
        context.goto_route("#balance")
        context.page.evaluate("if (typeof switchTab === 'function') switchTab('bank_interest');")
        context.page.wait_for_timeout(500)

        before_ids = interest_checker.snapshot_ids()

        context.page.evaluate("if (typeof showBankInterestModal === 'function') showBankInterestModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Bank Interest Modal")
        shot_bi = screenshot_logger.capture(context.page, "balance", "bank_interest_modal", "showBankInterestModal", "open", "ok")
        interest_checker.add_manual_step(context.page.query_selector("#bankInterestForm") is not None)

        bank_options = context.page.evaluate("(() => { const el = document.getElementById('bi_bank'); return el ? el.options.length : 0; })()")
        filled = False
        interest_amount = "75.00"
        if bank_options and bank_options > 1:
            context.page.select_option("#bi_bank", index=1)
            if context.page.query_selector("#bi_amount"):
                context.page.fill("#bi_amount", interest_amount)
                filled = True
            save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
            if save_btn and filled:
                save_btn.click()
                context.page.wait_for_timeout(800)
        else:
            context.page.evaluate("if (typeof closeModal === 'function') closeModal();")

        interest_checker.add_manual_step(filled)

        if filled:
            create_result = interest_checker.verify_created(before_ids, match_field="amount", expected_value=interest_amount)
            new_id = create_result.new_id

            if new_id is not None:
                context.page.evaluate(f"if (typeof showBankInterestModal === 'function') showBankInterestModal({new_id});")
                context.page.wait_for_timeout(600)
                new_amount = "95.00"
                if context.page.query_selector("#bi_amount"):
                    context.page.fill("#bi_amount", new_amount)
                    save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
                    if save_btn:
                        save_btn.click()
                        context.page.wait_for_timeout(800)
                context.page.evaluate("if (typeof closeModal === 'function') closeModal();")
                edit_result = interest_checker.verify_field_updated(new_id, "amount", new_amount)

                context.page.evaluate(f"(async () => {{ if (typeof deleteBankInterest === 'function') {{ await deleteBankInterest({new_id}); }} }})()")
                context.page.wait_for_timeout(1200)
                delete_result = interest_checker.verify_deleted(new_id)

                overall_pass = create_result.passed and edit_result.passed and delete_result.passed
                detail = f"Create: {create_result.detail} | Edit: {edit_result.detail} | Delete: {delete_result.detail}"
                status = "PASS" if overall_pass else "FAIL"
            else:
                detail = create_result.detail
                status = "FAIL"
        else:
            detail = "Skipped real save: no bank accounts exist yet to select from (needs prerequisite data)."
            status = "SKIP"

        reporter.record_crud("Bank Interest Entry", interest_checker.steps_passed, max(interest_checker.steps_total, 1))
        reporter.add_step("Bank Interest CRUD (API-verified)", "Balance & Net Worth", status, detail, screenshot_path=shot_bi)
    except Exception as ex:
        reporter.record_crud("Bank Interest Entry", interest_checker.steps_passed, max(interest_checker.steps_total, 1))
        reporter.add_step("Bank Interest Modal Test", "Balance & Net Worth", "FAIL", f"Exception: {ex}")

