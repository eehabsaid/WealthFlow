"""Balance module phase 6: Card Renewal Fee CRUD. Split out of tests/modules/balance.py."""

from tests.core.crud_verifier import CrudVerifier


def test_card_renewal_fee(context, reporter, screenshot_logger):
    # 6. Card Renewal Fee — real, API-verified. Also requires a bank to
    # charge, same skip-if-no-prerequisite-data convention as above.
    crf_checker = CrudVerifier(context.page, api_list_url="/api/card-renewal-fees/", list_key="card_renewal_fees")
    try:
        context.goto_route("#balance")
        context.page.evaluate("if (typeof switchTab === 'function') switchTab('card_renewal_fee');")
        context.page.wait_for_timeout(500)

        before_ids = crf_checker.snapshot_ids()

        context.page.evaluate("if (typeof showCardRenewalFeeModal === 'function') showCardRenewalFeeModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Card Renewal Fee Modal")
        shot_crf = screenshot_logger.capture(context.page, "balance", "card_renewal_fee_modal", "showCardRenewalFeeModal", "open", "ok")
        crf_checker.add_manual_step(context.page.query_selector("#cardRenewalFeeForm") is not None)

        bank_options = context.page.evaluate("(() => { const el = document.getElementById('crf_bank'); return el ? el.options.length : 0; })()")
        filled = False
        crf_amount = "35.00"
        if bank_options and bank_options > 1:
            context.page.select_option("#crf_bank", index=1)
            if context.page.query_selector("#crf_amount"):
                context.page.fill("#crf_amount", crf_amount)
                filled = True
            save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
            if save_btn and filled:
                save_btn.click()
                context.page.wait_for_timeout(800)
        else:
            context.page.evaluate("if (typeof closeModal === 'function') closeModal();")

        crf_checker.add_manual_step(filled)

        if filled:
            create_result = crf_checker.verify_created(before_ids, match_field="amount_egp", expected_value=crf_amount)
            new_id = create_result.new_id

            if new_id is not None:
                context.page.evaluate(f"if (typeof showCardRenewalFeeModal === 'function') showCardRenewalFeeModal({new_id});")
                context.page.wait_for_timeout(600)
                new_amount = "45.00"
                if context.page.query_selector("#crf_amount"):
                    context.page.fill("#crf_amount", new_amount)
                    save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
                    if save_btn:
                        save_btn.click()
                        context.page.wait_for_timeout(800)
                context.page.evaluate("if (typeof closeModal === 'function') closeModal();")
                edit_result = crf_checker.verify_field_updated(new_id, "amount_egp", new_amount)

                context.page.evaluate(f"(async () => {{ if (typeof deleteCardRenewalFee === 'function') {{ await deleteCardRenewalFee({new_id}); }} }})()")
                context.page.wait_for_timeout(1200)
                delete_result = crf_checker.verify_deleted(new_id)

                overall_pass = create_result.passed and edit_result.passed and delete_result.passed
                detail = f"Create: {create_result.detail} | Edit: {edit_result.detail} | Delete: {delete_result.detail}"
                status = "PASS" if overall_pass else "FAIL"
            else:
                detail = create_result.detail
                status = "FAIL"
        else:
            detail = "Skipped real save: no bank accounts exist yet to charge (needs prerequisite data)."
            status = "SKIP"

        reporter.record_crud("Card Renewal Fee Entry", crf_checker.steps_passed, max(crf_checker.steps_total, 1))
        reporter.add_step("Card Renewal Fee CRUD (API-verified)", "Balance & Net Worth", status, detail, screenshot_path=shot_crf)
    except Exception as ex:
        reporter.record_crud("Card Renewal Fee Entry", crf_checker.steps_passed, max(crf_checker.steps_total, 1))
        reporter.add_step("Card Renewal Fee Modal Test", "Balance & Net Worth", "FAIL", f"Exception: {ex}")

