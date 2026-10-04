"""WealthFlow QA Module - AI instant answers for Budgets and Recurring transactions.

Creates one throwaway budget and one recurring item for the E2E admin (through the real APIs), asks the REAL chat
endpoint about them, checks the answers (instant path, no model needed) and removes everything it created.
Questions that are advice ("how can I stay within my budget") are NOT asserted here: they need the model.
"""

_FETCH = """async ([url, method, body]) => {
  const res = await fetch(url, {method, headers: {"Content-Type": "application/json",
    "X-CSRFToken": (window.wfGetCsrfToken && window.wfGetCsrfToken()) || ""}, body: body ? JSON.stringify(body) : undefined});
  let data = null; try { data = await res.json(); } catch (e) {}
  return {status: res.status, data};
}"""

BUDGET_NAME = "E2E AI budget"
RECURRING_NAME = "E2E AI subscription"


def _step(reporter, screenshot_logger, page, name, ok, detail, shot_name):
    shot = screenshot_logger.capture(page, "ai", shot_name, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "WealthFlow AI", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def _ask(page, text):
    res = page.evaluate(_FETCH, ["/api/financial-advisor/ai/chat/", "POST", {"message": text}])
    content = ((res.get("data") or {}).get("message") or {}).get("content", "")
    return res["status"], content


def _run(context, reporter, screenshot_logger):
    from datetime import date, timedelta

    page = context.page
    context.goto_route("#ai")
    page.wait_for_selector("#ai-ws-input, #ai-chat-input", timeout=8000)
    base = page.evaluate("fetch('/api/base-currency/').then(r => r.json())")
    cur = (base or {}).get("code") or (base or {}).get("base_currency") or ""
    currencies = page.evaluate("fetch('/api/currencies/').then(r => r.json())")
    rows = currencies if isinstance(currencies, list) else (currencies or {}).get("currencies", [])
    cur_id = next((c["id"] for c in rows if c.get("code") == cur), rows[0]["id"] if rows else None)
    created = {}
    try:
        b = page.evaluate(_FETCH, ["/api/budgets/", "POST",
                                   {"name": BUDGET_NAME, "period": "monthly", "amount": 1000, "currency_id": cur_id, "alert_threshold_percent": 80}])
        r = page.evaluate(_FETCH, ["/api/recurring-transactions/", "POST",
                                   {"name": RECURRING_NAME, "amount": 25, "currency_id": cur_id, "frequency": "monthly", "interval": 1,
                                    "start_date": (date.today() + timedelta(days=3)).isoformat()}])
        created = {"budget": (b.get("data") or {}).get("id"), "recurring": (r.get("data") or {}).get("id")}
        ok = b["status"] == 201 and r["status"] == 201
        _step(reporter, screenshot_logger, page, "Throwaway budget and recurring item created", ok, f"budget={b['status']} recurring={r['status']}", "budgets_setup")
        if not ok:
            return

        status, text = _ask(page, "show my budgets")
        _step(reporter, screenshot_logger, page, "AI answers 'show my budgets' instantly with the real budget",
              status == 200 and BUDGET_NAME in text, f"status={status} has_budget={BUDGET_NAME in text}", "budgets_answer")

        status, text = _ask(page, "which budgets am I over")
        _step(reporter, screenshot_logger, page, "AI 'over budget' answer is a valid, non-error reply",
              status == 200 and bool(text.strip()), f"status={status} len={len(text)}", "budgets_over")

        status, text = _ask(page, "upcoming subscriptions")
        _step(reporter, screenshot_logger, page, "AI lists the upcoming recurring item", status == 200 and RECURRING_NAME in text,
              f"status={status} has_item={RECURRING_NAME in text}", "recurring_upcoming")

        status, text = _ask(page, "how much do my subscriptions cost per month")
        ok = status == 200 and (not cur or cur in text)
        _step(reporter, screenshot_logger, page, "AI recurring monthly total is in the user's own currency", ok,
              f"status={status} base={cur} in_answer={cur in text}", "recurring_total")
    finally:
        if created.get("budget"):
            page.evaluate(_FETCH, [f"/api/budgets/{created['budget']}/", "DELETE", None])
        if created.get("recurring"):
            page.evaluate(_FETCH, [f"/api/recurring-transactions/{created['recurring']}/", "DELETE", None])


def test_ai_budgets(context, reporter, screenshot_logger):
    try:
        _run(context, reporter, screenshot_logger)
    except Exception as ex:
        shot = screenshot_logger.capture(context.page, "ai", "budgets_error", "none", "fail", "fail")
        reporter.add_step("AI budgets/recurring answers", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot)
