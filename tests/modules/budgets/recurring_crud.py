"""Phase 3: Recurring transaction CRUD + safety rules (no back-fill, pause, read-only preview)."""

import time

from tests.core.crud_verifier import CrudVerifier

API = "/api/recurring-transactions/"


def _get_json(page, url):
    return page.evaluate(
        "async (u) => { const r = await fetch(u); return r.ok ? await r.json() : null; }", url
    )


def _count_expenses(page):
    data = _get_json(page, "/api/expenses/") or {}
    return len(data.get("entries", []))


def test_recurring_crud(context, reporter, screenshot_logger):
    page = context.page
    checker = CrudVerifier(page, api_list_url=API, list_key="recurring_transactions")
    name = f"E2E Recurring {str(int(time.time() * 1000))[-6:]}"
    try:
        context.goto_route("#budgets")
        before_ids = checker.snapshot_ids()
        expenses_before = _count_expenses(page)

        page.evaluate("if (typeof showRecurringModal === 'function') showRecurringModal(null);")
        page.wait_for_timeout(600)
        reporter.modals_opened.add("Recurring Transaction Modal")
        shot = screenshot_logger.capture(page, "budgets", "modal", "showRecurringModal", "open", "ok")
        checker.add_manual_step(page.query_selector("#rName") is not None)
        # Back-fill box must exist and be OFF by default (safety rule).
        backfill_off = page.query_selector("#rBackfill") is not None and not page.is_checked("#rBackfill")
        checker.add_manual_step(backfill_off)

        if page.query_selector("#rName"):
            page.fill("#rName", name)
            page.fill("#rAmount", "1")
            page.evaluate("document.getElementById('rStartDate').value = '2020-01-01'")  # long past
            page.evaluate("(async () => { if (typeof saveRecurring === 'function') { await saveRecurring(null); } })()")
            page.wait_for_timeout(900)
        created = checker.verify_created(before_ids, match_field="name", expected_value=name)

        # Safety rule 1: a past start date must NOT start in the past (no history back-fill).
        item = next((r for r in (_get_json(page, API) or {}).get("recurring_transactions", [])
                     if r.get("id") == created.new_id), {})
        today = time.strftime("%Y-%m-%d")
        no_backfill = bool(item) and item.get("next_run_date", "") >= today
        checker.add_manual_step(no_backfill)

        # Safety rule 2: the preview is read-only (expense count unchanged).
        preview = _get_json(page, API + "due-preview/")
        preview_ok = preview is not None and "due" in preview and _count_expenses(page) == expenses_before
        checker.add_manual_step(preview_ok)

        # Safety rule 3: pause / resume flips is_active.
        if created.new_id is not None:
            page.evaluate(f"(async () => {{ if (typeof toggleRecurringActive === 'function') {{ await toggleRecurringActive({created.new_id}, false); }} }})()")
            page.wait_for_timeout(800)
        paused = checker.verify_field_updated(created.new_id, "is_active", False)
        shot_paused = screenshot_logger.capture(page, "budgets", "recurring", "paused", "view", "ok")
        if created.new_id is not None:
            page.evaluate(f"(async () => {{ if (typeof toggleRecurringActive === 'function') {{ await toggleRecurringActive({created.new_id}, true); }} }})()")
            page.wait_for_timeout(800)

        new_name = name + " Edited"
        if created.new_id is not None:
            page.evaluate(f"if (typeof showRecurringModal === 'function') showRecurringModal({{id: {created.new_id}, name: '{name}', amount: 1, frequency: 'monthly', interval: 1, start_date: '2020-01-01', end_date: '', payment_method: 'Cash', is_active: true, notes: '', category_id: null, currency_code: null}});")
            page.wait_for_timeout(500)
            if page.query_selector("#rName"):
                page.fill("#rName", new_name)
                page.evaluate(f"(async () => {{ if (typeof saveRecurring === 'function') {{ await saveRecurring({created.new_id}); }} }})()")
                page.wait_for_timeout(900)
        edited = checker.verify_field_updated(created.new_id, "name", new_name)

        if created.new_id is not None:
            page.evaluate(f"(async () => {{ if (typeof deleteRecurring === 'function') {{ await deleteRecurring({created.new_id}); }} }})()")
            page.wait_for_timeout(900)
        deleted = checker.verify_deleted(created.new_id)

        ok = created.passed and paused.passed and edited.passed and deleted.passed and no_backfill and preview_ok and backfill_off
        reporter.record_crud("Recurring Transaction", checker.steps_passed, checker.steps_total)
        detail = (f"Create: {created.detail} | NoBackfill: {no_backfill} | BackfillBoxOffByDefault: {backfill_off} | "
                  f"PreviewReadOnly: {preview_ok} | Pause: {paused.detail} | Edit: {edited.detail} | Delete: {deleted.detail}")
        reporter.add_step("Recurring Transaction CRUD + safety rules (API-verified)", "Budgets",
                          "PASS" if ok else "FAIL", detail, screenshot_path=shot_paused or shot)
    except Exception as ex:
        shot_err = screenshot_logger.capture(page, "budgets", "recurring", "error", "fail", "fail")
        reporter.record_crud("Recurring Transaction", checker.steps_passed, max(checker.steps_total, 1))
        reporter.add_step("Recurring Transaction CRUD Test", "Budgets", "FAIL", f"Exception: {ex}", screenshot_path=shot_err)
