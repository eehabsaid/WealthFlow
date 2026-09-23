"""Balance module phase 3: Currency Exchange CRUD. Split out of tests/modules/balance.py."""

from tests.core.crud_verifier import CrudVerifier


def _pick_exchange_pair(balances):
    """Finds two balance entries with genuinely different currencies (the
    backend rejects a same-currency exchange with same_currency_error), and
    an amount to move that the 'from' balance can actually afford."""
    usable = [b for b in balances if (b.get("amount") or 0) > 0]
    usable.sort(key=lambda b: b.get("amount") or 0, reverse=True)
    for from_b in usable:
        for to_b in usable:
            if to_b["id"] == from_b["id"]:
                continue
            if to_b.get("currency_code") == from_b.get("currency_code"):
                continue
            amount = round(min(1.0, from_b["amount"] * 0.5), 2)
            if amount <= 0:
                continue
            return from_b, to_b, amount
    return None, None, None


def test_currency_exchange(context, reporter, screenshot_logger):
    # 3. Currency Exchange — real, API-verified. Requires 2 balance entries
    # in different currencies (the backend rejects same-currency exchanges);
    # if that data doesn't exist, only the modal's structural presence is
    # verified (same convention as Bank Interest / Credit Card Payment).
    exchange_checker = CrudVerifier(context.page, api_list_url="/api/currency-exchanges/", list_key="exchanges")
    try:
        context.goto_route("#balance")
        context.page.evaluate("if (typeof switchTab === 'function') switchTab('currency_exchange');")
        context.page.wait_for_timeout(500)

        before_ids = exchange_checker.snapshot_ids()

        options = context.page.evaluate(
            """async () => {
                const res = await fetch("/api/currency-exchanges/options/");
                if (!res.ok) return null;
                return await res.json();
            }"""
        )
        balances = (options or {}).get("balances", [])
        from_b, to_b, amount = _pick_exchange_pair(balances)

        context.page.evaluate("if (typeof showExchangeModal === 'function') showExchangeModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Currency Exchange Modal")
        shot_ce = screenshot_logger.capture(context.page, "balance", "currency_exchange_modal", "showExchangeModal", "open", "ok")
        exchange_checker.add_manual_step(context.page.query_selector("#exchangeForm") is not None)

        filled = False
        from_amount_str = f"{amount:.2f}" if amount else None
        if from_b is not None:
            context.page.select_option("#ce_from_balance", value=str(from_b["id"]))
            context.page.wait_for_timeout(400)
            context.page.select_option("#ce_to_balance", value=str(to_b["id"]))
            context.page.wait_for_timeout(400)
            context.page.fill("#ce_from_amount", from_amount_str)
            context.page.wait_for_timeout(500)
            save_btn = context.page.query_selector("#saveExchangeBtn")
            if save_btn:
                save_btn.click()
                context.page.wait_for_timeout(800)
                filled = True
        else:
            context.page.evaluate("if (typeof closeModal === 'function') closeModal();")

        exchange_checker.add_manual_step(filled)

        if filled:
            create_result = exchange_checker.verify_created(before_ids, match_field="from_amount", expected_value=from_amount_str)
            new_id = create_result.new_id

            if new_id is not None:
                context.page.evaluate(f"if (typeof showExchangeModal === 'function') showExchangeModal({new_id});")
                context.page.wait_for_timeout(600)
                new_amount_str = f"{round(amount / 2, 2):.2f}"
                context.page.fill("#ce_from_amount", new_amount_str)
                context.page.wait_for_timeout(500)
                save_btn = context.page.query_selector("#saveExchangeBtn")
                if save_btn:
                    save_btn.click()
                    context.page.wait_for_timeout(800)
                edit_result = exchange_checker.verify_field_updated(new_id, "from_amount", new_amount_str)

                # "Delete" reverses the exchange rather than removing the row
                # (see CurrencyExchangeDetailView.delete) — the row stays
                # visible via the API with status=REVERSED, so we check that
                # status flip instead of the row's absence.
                context.page.evaluate(f"(async () => {{ if (typeof deleteExchange === 'function') {{ await deleteExchange({new_id}); }} }})()")
                context.page.wait_for_timeout(1200)
                delete_result = exchange_checker.verify_field_updated(new_id, "status", "REVERSED")

                overall_pass = create_result.passed and edit_result.passed and delete_result.passed
                detail = f"Create: {create_result.detail} | Edit: {edit_result.detail} | Reverse (delete): {delete_result.detail}"
                status = "PASS" if overall_pass else "FAIL"
            else:
                detail = create_result.detail
                status = "FAIL"
        else:
            detail = "Skipped real save: no 2 balance entries in different currencies with a usable amount exist yet (needs prerequisite data)."
            status = "SKIP"

        reporter.record_crud("Currency Exchange Entry", exchange_checker.steps_passed, max(exchange_checker.steps_total, 1))
        reporter.add_step("Currency Exchange CRUD (API-verified)", "Balance & Net Worth", status, detail, screenshot_path=shot_ce)
    except Exception as ex:
        reporter.record_crud("Currency Exchange Entry", exchange_checker.steps_passed, max(exchange_checker.steps_total, 1))
        reporter.add_step("Currency Exchange Modal Test", "Balance & Net Worth", "FAIL", f"Exception: {ex}")
