"""WealthFlow QA Module - AI salary list + Excel export.

Creates one throwaway company with two salary entries in a far-away year (through the real APIs), asks the REAL
chat endpoint to list that year and export it, checks the instant answer (table + download link, no model needed),
downloads the .xlsx through the browser from that very link and removes everything it created.
"""

from tests.core.download_verifier import verify_downloaded_file

_FETCH = """async ([url, method, body]) => {
  const res = await fetch(url, {method, headers: {"Content-Type": "application/json",
    "X-CSRFToken": (window.wfGetCsrfToken && window.wfGetCsrfToken()) || ""}, body: body ? JSON.stringify(body) : undefined});
  let data = null; try { data = await res.json(); } catch (e) {}
  return {status: res.status, data};
}"""

COMPANY = "E2E AI salary export"
YEAR = 2098
QUESTION = f"please list the paid salaries for year {YEAR}, and export it in excel sheet"


def _step(reporter, screenshot_logger, page, name, ok, detail, shot_name):
    shot = screenshot_logger.capture(page, "ai", shot_name, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "WealthFlow AI", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def _run(context, reporter, screenshot_logger):
    import re

    page = context.page
    context.goto_route("#ai")
    page.wait_for_selector("#ai-ws-input, #ai-chat-input", timeout=8000)
    company_id = None
    try:
        c = page.evaluate(_FETCH, ["/api/companies/", "POST", {"name": COMPANY, "display_name": COMPANY}])
        company_id = (c.get("data") or {}).get("id")
        statuses = [c["status"]]
        for month, paid in (("January", 1111.11), ("February", 2222.22)):
            s = page.evaluate(_FETCH, ["/api/salary/", "POST", {"company_id": company_id, "year": YEAR, "month": month, "expected": paid, "paid": paid}])
            statuses.append(s["status"])
        ok = statuses == [201, 201, 201]
        _step(reporter, screenshot_logger, page, "Throwaway salary entries created", ok, f"statuses={statuses}", "salary_export_setup")
        if not ok:
            return

        res = page.evaluate(_FETCH, ["/api/financial-advisor/ai/chat/", "POST", {"message": QUESTION}])
        text = ((res.get("data") or {}).get("message") or {}).get("content", "")
        link = re.search(r"\]\((/api/salary/export/[^)\s]+)\)", text)
        ok = res["status"] == 200 and "1,111.11" in text and "2,222.22" in text and bool(link)
        _step(reporter, screenshot_logger, page, "AI lists the year's salaries and offers an Excel link instantly", ok,
              f"status={res['status']} rows={'1,111.11' in text and '2,222.22' in text} link={link.group(1) if link else None}", "salary_export_answer")
        if not link:
            return

        with page.expect_download(timeout=8000) as info:
            page.evaluate(f"window.location.href = {link.group(1)!r}")
        download = info.value
        path = f"test_downloads/{download.suggested_filename}"
        download.save_as(path)
        verify_downloaded_file(path, expected_extension=".xlsx")
        reporter.exports_tested.append("WealthFlow AI -> salary list Excel download")
        _step(reporter, screenshot_logger, page, "Excel link downloads a valid .xlsx", True, f"saved {path}", "salary_export_download")
    finally:
        if company_id:
            page.evaluate(_FETCH, [f"/api/companies/{company_id}/", "DELETE", None])


def test_ai_salary_export(context, reporter, screenshot_logger):
    try:
        _run(context, reporter, screenshot_logger)
    except Exception as ex:
        shot = screenshot_logger.capture(context.page, "ai", "salary_export_error", "none", "fail", "fail")
        reporter.add_step("AI salary list + Excel export", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot)
