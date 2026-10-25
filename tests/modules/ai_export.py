"""WealthFlow QA Module - AI downloadable answers (Excel / Word / PDF).

Creates one throwaway company with two salary entries in a far-away year (through the real APIs), then in the REAL chat UI
asks for the year's salaries "in excel, word and pdf": checks the table and the three download links, clicks each link and
verifies the downloaded .xlsx / .docx / .pdf. A bare "export it to pdf" follow-up must export the previous answer (no model),
and another user's / unknown message ids must answer 404. Everything it created is removed at the end.
"""

import re

from tests.core.download_verifier import verify_downloaded_file
from tests.modules.e2e_settings import AI_ENGINE_PINS, django_exec, pinned, rows

_FETCH = """async ([url, method, body]) => {
  const res = await fetch(url, {method, headers: {"Content-Type": "application/json",
    "X-CSRFToken": (window.wfGetCsrfToken && window.wfGetCsrfToken()) || ""}, body: body ? JSON.stringify(body) : undefined});
  let data = null; try { data = await res.json(); } catch (e) {}
  return {status: res.status, data};
}"""
CHAT = "/api/financial-advisor/ai/chat/"
COMPANY = "E2E AI export"
YEAR = 2098
FORMATS = (("xlsx", "Excel"), ("docx", "Word"), ("pdf", "PDF"))
QUESTION = f"please list the paid salaries for year {YEAR}, and export it in excel, word and pdf"


def _step(reporter, screenshot_logger, page, name, ok, detail, shot_name):
    shot = screenshot_logger.capture(page, "ai", shot_name, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "WealthFlow AI", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def _download(page, link_locator, extension):
    with page.expect_download(timeout=10000) as info:
        link_locator.click()
    download = info.value
    path = f"test_downloads/{download.suggested_filename}"
    download.save_as(path)
    verify_downloaded_file(path, expected_extension=f".{extension}")
    return path


def _footer_step(page, reporter, screenshot_logger, path):
    """The downloaded Word file has a footer with a live PAGE field on its pages."""
    import zipfile

    with zipfile.ZipFile(path) as z:
        xml = "".join(z.read(n).decode("utf8") for n in z.namelist() if n.startswith("word/footer"))
    _step(reporter, screenshot_logger, page, "Word file has a footer with a page-number field", "PAGE" in xml, f"footer_has_PAGE={'PAGE' in xml}", "export_docx_footer")


def _ask_in_ui(page, text):
    before = page.locator("a.ai-ws-link").count()
    page.fill("#ai-ws-input", text)
    page.click(".ai-ws-send-btn")
    page.wait_for_function("(n) => document.querySelectorAll('a.ai-ws-link').length >= n + 3", arg=before, timeout=25000)
    page.wait_for_timeout(600)


def _run(context, reporter, screenshot_logger):
    page = context.page
    context.goto_route("#ai")
    page.wait_for_selector("#ai-ws-input", timeout=10000)
    page.evaluate("""async () => {
      if (typeof _aiLoadChatMode === "function") await _aiLoadChatMode();
      if (typeof _aiSetChatMode === "function") await _aiSetChatMode("ask");
    }""")
    page.wait_for_function("() => document.getElementById('ai-ws-mode-ask')?.getAttribute('aria-pressed') === 'true'")
    company_id = None
    try:
        c = page.evaluate(_FETCH, ["/api/companies/", "POST", {"name": COMPANY, "display_name": COMPANY}])
        company_id = (c.get("data") or {}).get("id")
        statuses = [c["status"]]
        for month, paid in (("January", 1111.11), ("February", 2222.22)):
            s = page.evaluate(_FETCH, ["/api/salary/", "POST", {"company_id": company_id, "year": YEAR, "month": month, "expected": paid, "paid": paid}])
            statuses.append(s["status"])
        ok = statuses == [201, 201, 201]
        _step(reporter, screenshot_logger, page, "Throwaway salary entries created", ok, f"statuses={statuses}", "export_setup")
        if not ok:
            return

        _ask_in_ui(page, QUESTION)
        links = page.locator("a.ai-ws-link")
        texts = [links.nth(links.count() - 3 + i).inner_text() for i in range(3)]
        table_ok = page.locator(".ai-table-wrap").last.inner_text().count("2,222.22") >= 1
        ok = table_ok and all(label in text for (_, label), text in zip(FORMATS, texts))
        _step(reporter, screenshot_logger, page, "Chat shows the year's table and Excel / Word / PDF download links", ok,
              f"table={table_ok} links={texts}", "export_answer")

        for index, (extension, label) in enumerate(FORMATS):
            link = page.locator("a.ai-ws-link").nth(page.locator("a.ai-ws-link").count() - 3 + index)
            path = _download(page, link, extension)
            reporter.exports_tested.append(f"WealthFlow AI -> {label} answer download")
            _step(reporter, screenshot_logger, page, f"{label} link downloads a valid .{extension}", True, f"saved {path}", f"export_{extension}")
            if extension == "docx":
                _footer_step(page, reporter, screenshot_logger, path)

        first = page.evaluate(_FETCH, [CHAT, "POST", {"message": f"list the paid salaries for year {YEAR}"}])
        convo = (first.get("data") or {}).get("conversation_id")
        follow = page.evaluate(_FETCH, [CHAT, "POST", {"message": "export it to pdf", "conversation_id": convo}])
        message = (follow.get("data") or {}).get("message") or {}
        target = (first.get("data") or {}).get("message", {}).get("id")
        found = re.findall(r"/messages/(\d+)/export/(\w+)/", message.get("content", ""))
        ok = follow["status"] == 200 and found == [(str(target), "pdf")] and (message.get("tool_calls") or [{}])[0].get("tool") == "export_followup"
        _step(reporter, screenshot_logger, page, "Bare 'export it to pdf' exports the previous answer", ok, f"links={found} target={target}", "export_followup")

        _direct_answers_off_step(page, reporter, screenshot_logger)
        _full_data_steps(page, reporter, screenshot_logger)

        cards = page.locator("a.ai-ws-file").count()
        _step(reporter, screenshot_logger, page, "Chat renders the downloads as cards with a format badge", cards >= 3 and page.locator(".ai-ws-file-ext").count() >= 3, f"cards={cards}", "export_cards")

        missing = page.evaluate(_FETCH, ["/api/financial-advisor/ai/messages/0/export/xlsx/", "GET", None])
        bad_format = page.evaluate(_FETCH, [f"/api/financial-advisor/ai/messages/{target}/export/exe/", "GET", None])
        ok = missing["status"] == 404 and bad_format["status"] == 404
        _step(reporter, screenshot_logger, page, "Unknown message id and unknown format answer 404", ok, f"id0={missing['status']} exe={bad_format['status']}", "export_404")
    finally:
        if company_id:
            page.evaluate(_FETCH, [f"/api/companies/{company_id}/", "DELETE", None])


BULK = 350
BULK_FIXTURE = (
    "import datetime; from decimal import Decimal; from django.contrib.auth import get_user_model; from core.models import Expense, ExpenseCategory\n"
    "u = get_user_model().objects.get(username='eehab_said'); c, _ = ExpenseCategory.objects.get_or_create(owner=u, name='E2E bulk cat')\n"
    f"Expense.objects.bulk_create([Expense(owner=u, category=c, date=datetime.date({YEAR}, 6, 1 + i % 25), year={YEAR}, month=6, amount=Decimal('1'), amount_base=Decimal('1'), description=f'E2E bulk {{i}}') for i in range({BULK})])\n"
)
BULK_CLEANUP = "from core.models import Expense, ExpenseCategory; Expense.objects.filter(description__startswith='E2E bulk ').delete(); ExpenseCategory.objects.filter(name='E2E bulk cat').delete()"


def _full_data_steps(page, reporter, screenshot_logger):
    """The file must hold EVERY row (the chat table stops at 300), straight from the database, with the file switch honoured."""
    from openpyxl import load_workbook

    django_exec(BULK_FIXTURE)
    try:
        want = rows("SELECT COUNT(*) FROM core_expense WHERE description LIKE 'E2E bulk %'")[0][0]
        res = page.evaluate(_FETCH, [CHAT, "POST", {"message": f"list my expenses for June {YEAR} and export to excel"}])
        message = (res.get("data") or {}).get("message") or {}
        found = re.findall(r"/messages/(\d+)/export/(\w+)/", message.get("content", ""))
        path = None
        if found:
            with page.expect_download(timeout=15000) as info:
                page.evaluate(f"window.location.href = '/api/financial-advisor/ai/messages/{found[0][0]}/export/xlsx/'")
            path = f"test_downloads/{info.value.suggested_filename}"
            info.value.save_as(path)
        got = sum(1 for r in load_workbook(path).active.iter_rows(values_only=True) if r and any(str(c).startswith("E2E bulk ") for c in r if c)) if path else -1
        _step(reporter, screenshot_logger, page, f"Excel holds all {want} expense rows, not just the chat table's first 300", got == want == BULK,
              f"rows_in_file={got} rows_in_db={want} chat_note={'Showing the first' in message.get('content', '')}", "export_full_data")
        with pinned({"ai_file_generation": "false"}):
            off = page.evaluate(_FETCH, [CHAT, "POST", {"message": f"list my expenses for June {YEAR} and export to excel"}])
            gone = page.evaluate(_FETCH, [f"/api/financial-advisor/ai/messages/{found[0][0]}/export/xlsx/", "GET", None]) if found else {"status": 0}
            no_link = "/export/" not in (((off.get("data") or {}).get("message") or {}).get("content", ""))
            _step(reporter, screenshot_logger, page, "File generation switch OFF: no links, old links answer 404", no_link and gone["status"] == 404,
                  f"no_link={no_link} old_link={gone['status']}", "export_switch_off")
    finally:
        django_exec(BULK_CLEANUP)


def _direct_answers_off_step(page, reporter, screenshot_logger):
    """With Instant Answers OFF the file is still built from the database (the model's wording does not matter)."""
    with pinned({**AI_ENGINE_PINS, "ai_direct_answers": "false"}):
        res = page.evaluate(_FETCH, [CHAT, "POST", {"message": f"please list the paid salaries for year {YEAR}, and export it in excel"}])
        message = (res.get("data") or {}).get("message") or {}
        found = re.findall(r"/messages/(\d+)/export/(\w+)/", message.get("content", ""))
        ok = bool(found)
        if found:
            with page.expect_download(timeout=15000) as info:
                page.evaluate(f"window.location.href = '/api/financial-advisor/ai/messages/{found[0][0]}/export/xlsx/'")
            from openpyxl import load_workbook

            path = f"test_downloads/{info.value.suggested_filename}"
            info.value.save_as(path)
            cells = [c for r in load_workbook(path).active.iter_rows(values_only=True) for c in r if isinstance(c, (int, float))]
            db = [float(p) for (p,) in rows("SELECT s.paid FROM core_salaryentry s JOIN core_company c ON c.id = s.company_id WHERE c.name = ? AND s.year = ?", (COMPANY, YEAR))]
            ok = all(any(abs(c - d) < 0.01 for c in cells) for d in db) and len(db) == 2
        _step(reporter, screenshot_logger, page, "Instant Answers OFF: the Excel still holds the database rows", ok, f"links={found}", "export_direct_off")


def test_ai_export(context, reporter, screenshot_logger):
    try:
        # Every precondition is pinned: the runner copies the developer's real db.sqlite3 (ai_direct_answers=false there)
        # and a fresh DB has no provider at all.
        with pinned({**AI_ENGINE_PINS, "ai_direct_answers": "true"}):
            _run(context, reporter, screenshot_logger)
    except Exception as ex:
        shot = screenshot_logger.capture(context.page, "ai", "export_error", "none", "fail", "fail")
        reporter.add_step("AI downloadable answers", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot)
