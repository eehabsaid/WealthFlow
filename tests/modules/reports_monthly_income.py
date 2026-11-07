"""
WealthFlow QA Module — Expenses Report: per-month Total Income (editable).
Checks that the editable income card stores its manual amount per month: editing month A changes only month A,
the value is saved through /api/expenses/manual-income/, and the Yearly tab card is read-only.
"""

EDIT_AMOUNT = 123456.78
PAGE = "Expenses Report"


def _income_value(page):
    page.wait_for_timeout(1200)
    text = page.inner_text("#reportKPIs .kpi-value")
    return float(text.replace(",", "").strip())


def _select_month(page, month):
    page.select_option("#rMonth", str(month))
    page.wait_for_timeout(300)


def _edit_income(page, amount):
    page.evaluate(f"window.prompt = () => '{amount}'")
    page.click("#reportKPIs .col-6 >> nth=0")


def _api_amount(page, year, month):
    return page.evaluate(
        "async ([y, m]) => (await (await fetch(`/api/expenses/manual-income/?year=${y}&month=${m}`)).json()).amount",
        [year, month],
    )


def test_reports_monthly_income(context, reporter):
    page = context.page
    context.goto_route("#reports")
    page.evaluate("renderReports()")  # re-render: opens the Monthly tab (earlier steps may leave another tab active)
    page.wait_for_selector("#reportKPIs .kpi-value", timeout=8000)
    year = page.evaluate("currentReportYear")
    month_a, month_b = 9, 10
    try:
        _select_month(page, month_a)
        base_a = _income_value(page)
        _select_month(page, month_b)
        base_b = _income_value(page)

        _select_month(page, month_a)
        _edit_income(page, EDIT_AMOUNT)
        edited_a = _income_value(page)
        assert abs(edited_a - (base_a + EDIT_AMOUNT)) < 0.01, f"month {month_a}: {base_a} -> {edited_a}"
        assert abs(_api_amount(page, year, month_a) - EDIT_AMOUNT) < 0.01, "manual income not saved by the API"

        _select_month(page, month_b)
        assert abs(_income_value(page) - base_b) < 0.01, f"month {month_b} changed when month {month_a} was edited"
        assert _api_amount(page, year, month_b) == 0, f"month {month_b} has a stored manual income"

        reporter.add_step("Monthly Income Is Per Month", PAGE, "PASS", f"{month_a}: {base_a} -> {edited_a}; {month_b} stays {base_b}")
    except Exception as ex:
        reporter.add_step("Monthly Income Is Per Month", PAGE, "FAIL", f"Exception: {ex}")
    finally:
        _select_month(page, month_a)
        _edit_income(page, 0)
        page.wait_for_timeout(800)

    try:
        context.page.evaluate("switchReportTab('yearly')")
        page.wait_for_timeout(800)
        has_handler = page.evaluate("document.querySelector('#reportKPIs .col-6').hasAttribute('onclick')")
        assert not has_handler, "Yearly income card must be read-only"
        reporter.add_step("Yearly Income Card Read-Only", PAGE, "PASS", "No edit handler on the Yearly tab")
    except Exception as ex:
        reporter.add_step("Yearly Income Card Read-Only", PAGE, "FAIL", f"Exception: {ex}")
