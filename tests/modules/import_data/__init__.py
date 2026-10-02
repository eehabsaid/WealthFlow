"""
WealthFlow QA Module — Import Data: CSV/Excel statement import (A3)
Tests, through the real UI (file chooser -> mapping preview -> Confirm Import):
 1. #import-data route renders and the file input is present.
 2. Upload a CSV: column-mapping UI appears with date/amount/description auto-mapped.
 3. Confirm import: expenses really appear via /api/expenses/ (API-verified).
 4. Re-import the SAME file: duplicates are detected and skipped (0 new rows).
 5. Unsupported file type is rejected with error_key=unsupported_file_type.
 Created expenses are deleted afterwards.

If the test account lacks the Cash balance needed to deduct an expense, the
import step is reported as SKIP (precondition), never as a false PASS.

NOTE: tests/core/test_context.py already registers the global dialog handler.
"""

import os
import tempfile
import time

IMPORT_BALANCE_ERRORS = ("matching_balance_entry_not_found", "insufficient_balance", "bank_account_required",
                         "exchange_rate_missing")


def _list_expenses(page):
    data = page.evaluate("async () => { const r = await fetch('/api/expenses/'); return r.ok ? await r.json() : null; }")
    return (data or {}).get("entries", [])


def _upload_and_confirm(page, path):
    page.set_input_files("input[type=file]", path)
    page.wait_for_selector("#mapDate", timeout=8000)
    mapping = page.evaluate("({date: document.getElementById('mapDate').value, "
                            "amount: document.getElementById('mapAmount').value, "
                            "description: document.getElementById('mapDescription').value})")
    with page.expect_response(lambda r: "/api/import/confirm/" in r.url, timeout=15000) as info:
        page.click("button[onclick='confirmImport()']")
    return mapping, info.value.json()


def test_import_data_module(context, reporter, screenshot_logger):
    page = context.page
    uid = str(int(time.time() * 1000))[-6:]
    descs = [f"E2E Import A {uid}", f"E2E Import B {uid}"]
    today = time.strftime("%Y-%m-%d")
    fd, path = tempfile.mkstemp(suffix=".csv")
    created_ids = []
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("Date,Amount,Description\n")
            for d in descs:
                f.write(f"{today},1.00,{d}\n")

        context.goto_route("#import-data")
        reporter.pages_visited.add("Import Data")
        has_input = page.query_selector("input[type=file]") is not None
        shot = screenshot_logger.capture(page, "import", "page", "none", "view", "ok")
        reporter.add_step("Import Data page renders", "Import Data", "PASS" if has_input else "FAIL",
                          "File input present." if has_input else "File input missing.", screenshot_path=shot)

        # Unsupported type is rejected by the real endpoint.
        bad = page.evaluate("""async () => {
            const fd = new FormData();
            fd.append('file', new Blob(['x'], {type: 'application/pdf'}), 'statement.pdf');
            const r = await fetch('/api/import/preview/', {method: 'POST', body: fd});
            return {status: r.status, body: await r.json()};
        }""")
        bad_ok = bad["status"] == 400 and bad["body"].get("error_key") == "unsupported_file_type"
        reporter.add_step("Import rejects unsupported file type", "Import Data", "PASS" if bad_ok else "FAIL", str(bad))

        before_ids = {e["id"] for e in _list_expenses(page)}
        page.set_input_files("input[type=file]", path)
        page.wait_for_selector("#mapDate", timeout=8000)
        reporter.modals_opened.add("Import Column Mapping")
        reporter.tabs_visited.add("Import Data -> mapping")
        shot_map = screenshot_logger.capture(page, "import", "mapping", "none", "preview", "ok")
        auto = page.evaluate("[document.getElementById('mapDate').value, document.getElementById('mapAmount').value, "
                             "document.getElementById('mapDescription').value]")
        map_ok = auto == ["Date", "Amount", "Description"]
        reporter.add_step("Import preview auto-maps columns", "Import Data", "PASS" if map_ok else "FAIL",
                          f"Auto-mapped: {auto}", screenshot_path=shot_map)

        context.goto_route("#import-data")
        mapping, result = _upload_and_confirm(page, path)
        shot_done = screenshot_logger.capture(page, "import", "confirm", "none", "done", "ok")
        reasons = [e.get("reason") for e in result.get("errors", [])]
        if result.get("created_count", 0) == 2:
            new = [e for e in _list_expenses(page) if e["id"] not in before_ids and e.get("description") in descs]
            created_ids = [e["id"] for e in new]
            ok = len(new) == 2
            reporter.record_crud("Import Data", 2 if ok else 1, 2)
            reporter.add_step("Import creates expenses (API-verified)", "Import Data", "PASS" if ok else "FAIL",
                              f"created_count=2, found {len(new)} rows via /api/expenses/.", screenshot_path=shot_done)

            context.goto_route("#import-data")
            _, again = _upload_and_confirm(page, path)
            dup_ok = again.get("created_count") == 0 and again.get("skipped_duplicate_count") == 2
            reporter.add_step("Re-import skips duplicates", "Import Data", "PASS" if dup_ok else "FAIL",
                              f"second run: created={again.get('created_count')}, skipped={again.get('skipped_duplicate_count')}")
        elif any(r in IMPORT_BALANCE_ERRORS for r in reasons):
            reporter.add_step("Import creates expenses (API-verified)", "Import Data", "SKIP",
                              f"Account lacks the cash/bank balance needed to post expenses: {sorted(set(reasons))}",
                              screenshot_path=shot_done)
        else:
            reporter.add_step("Import creates expenses (API-verified)", "Import Data", "FAIL",
                              f"created_count={result.get('created_count')}, errors={reasons}", screenshot_path=shot_done)
    except Exception as ex:
        shot_err = screenshot_logger.capture(page, "import", "flow", "error", "fail", "fail")
        reporter.add_step("Import Data flow", "Import Data", "FAIL", f"Exception: {ex}", screenshot_path=shot_err)
    finally:
        for eid in created_ids:
            page.evaluate(f"(async () => {{ await fetch('/api/expenses/{eid}/', {{method: 'DELETE'}}); }})()")
        page.wait_for_timeout(500)
        try:
            os.remove(path)
        except OSError:
            pass
