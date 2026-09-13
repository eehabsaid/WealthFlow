"""Balance module phase 2: Balance Transfer CRUD (Transfer Modal). Split out of tests/modules/balance.py."""

from tests.core.crud_verifier import CrudVerifier


def test_transfers(context, reporter, screenshot_logger):
    # 2. Balance Transfer — real, API-verified (was: open modal, screenshot, close — no data entered at all)
    transfer_checker = CrudVerifier(context.page, api_list_url="/api/balance-transfers/", list_key="transfers")
    try:
        context.goto_route("#balance")
        context.page.evaluate("if (typeof switchTab === 'function') switchTab('transfers');")
        context.page.wait_for_timeout(500)

        before_ids = transfer_checker.snapshot_ids()

        context.page.evaluate("if (typeof showTransferModal === 'function') showTransferModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Balance Transfer Modal")
        shot_tr = screenshot_logger.capture(context.page, "balance", "transfer_modal", "showTransferModal", "open", "ok")
        transfer_checker.add_manual_step(context.page.query_selector("#transferForm") is not None)

        # Requires at least 2 existing balance accounts to select from —
        # only attempt the actual save if the form's bank selects have options.
        from_options = context.page.evaluate("(() => { const el = document.getElementById('tr_from_bank'); return el ? el.options.length : 0; })()")
        filled = False
        transfer_amount = "50.00"
        if from_options and from_options > 1:
            context.page.select_option("#tr_from_bank", index=1)
            context.page.select_option("#tr_to_bank", index=min(2, from_options - 1))
            if context.page.query_selector("#tr_amount"):
                context.page.fill("#tr_amount", transfer_amount)
                filled = True
            save_btn = context.page.query_selector("#globalModal button[type='submit'], #globalModal .btn-primary-custom, #globalModal button:has-text('Save')")
            if save_btn and filled:
                save_btn.click()
                context.page.wait_for_timeout(800)
        else:
            context.page.evaluate("if (typeof closeModal === 'function') closeModal();")

        transfer_checker.add_manual_step(filled)

        if filled:
            create_result = transfer_checker.verify_created(before_ids, match_field="amount", expected_value=transfer_amount)
            detail = create_result.detail
            status = "PASS" if create_result.passed else "FAIL"
        else:
            detail = "Skipped real save: fewer than 2 balance accounts exist to transfer between (needs prerequisite data)."
            status = "SKIP"

        reporter.record_crud("Balance Transfer Entry", transfer_checker.steps_passed, max(transfer_checker.steps_total, 1))
        reporter.add_step("Balance Transfer CRUD (API-verified)", "Balance & Net Worth", status, detail, screenshot_path=shot_tr)
    except Exception as ex:
        reporter.record_crud("Balance Transfer Entry", transfer_checker.steps_passed, max(transfer_checker.steps_total, 1))
        reporter.add_step("Balance Transfer Modal Test", "Balance & Net Worth", "FAIL", f"Exception: {ex}")

