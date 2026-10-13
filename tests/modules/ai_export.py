"""WealthFlow QA Module - AI downloadable answers (Excel / Word / PDF).

Creates one throwaway company with two salary entries in a far-away year (through the real APIs), then in the REAL chat UI
asks for the year's salaries "in excel, word and pdf": checks the table and the three download links, clicks each link and
verifies the downloaded .xlsx / .docx / .pdf. A bare "export it to pdf" follow-up must export the previous answer (no model),
and another user's / unknown message ids must answer 404. Everything it created is removed at the end.
"""

import re

from tests.core.download_verifier import verify_downloaded_file

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

        first = page.evaluate(_FETCH, [CHAT, "POST", {"message": f"list the paid salaries for year {YEAR}"}])
        convo = (first.get("data") or {}).get("conversation_id")
        follow = page.evaluate(_FETCH, [CHAT, "POST", {"message": "export it to pdf", "conversation_id": convo}])
        message = (follow.get("data") or {}).get("message") or {}
        target = (first.get("data") or {}).get("message", {}).get("id")
        found = re.findall(r"/messages/(\d+)/export/(\w+)/", message.get("content", ""))
        ok = follow["status"] == 200 and found == [(str(target), "pdf")] and (message.get("tool_calls") or [{}])[0].get("tool") == "export_followup"
        _step(reporter, screenshot_logger, page, "Bare 'export it to pdf' exports the previous answer", ok, f"links={found} target={target}", "export_followup")

        missing = page.evaluate(_FETCH, ["/api/financial-advisor/ai/messages/0/export/xlsx/", "GET", None])
        bad_format = page.evaluate(_FETCH, [f"/api/financial-advisor/ai/messages/{target}/export/exe/", "GET", None])
        ok = missing["status"] == 404 and bad_format["status"] == 404
        _step(reporter, screenshot_logger, page, "Unknown message id and unknown format answer 404", ok, f"id0={missing['status']} exe={bad_format['status']}", "export_404")
    finally:
        if company_id:
            page.evaluate(_FETCH, [f"/api/companies/{company_id}/", "DELETE", None])


def test_ai_export(context, reporter, screenshot_logger):
    try:
        _run(context, reporter, screenshot_logger)
    except Exception as ex:
        shot = screenshot_logger.capture(context.page, "ai", "export_error", "none", "fail", "fail")
        reporter.add_step("AI downloadable answers", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot)
