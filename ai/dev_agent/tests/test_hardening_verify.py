"""Hardening 5: verification reporting separates passed / failed / skipped / not run, always says what happened to browser E2E,
and never says VERIFIED unless an automated test really ran and passed."""

from ai.dev_agent.engine import report, verify

P = lambda step: {"step": step, "status": "PASSED", "detail": ""}  # noqa: E731


def test_verified_needs_a_passing_automated_test():
    assert verify.overall([P("pyflakes"), P("line limit (200)")]) == "NOT VERIFIED (no automated test ran)"
    assert verify.overall([P("pyflakes"), P("django tests")]) == "VERIFIED"
    assert verify.overall([P("django tests"), {"step": "browser E2E", "status": "NOT RUN", "detail": "no browser"}]).startswith("NOT VERIFIED")
    assert verify.overall([P("django tests"), {"step": "x", "status": "FAILED", "detail": ""}]) == "FAILED"
    assert verify.overall([{"step": "checks", "status": "SKIPPED", "detail": "no files"}]) == "NOT VERIFIED (nothing ran)"
    assert verify.overall([P("test mapping")]) == "NOT VERIFIED (no automated test ran)"   # the mapping row is not a test


def test_counts_and_tests_line_keep_each_status_apart():
    rows = [P("pyflakes"), P("django tests"), {"step": "pytest (dev_agent)", "status": "FAILED", "detail": "boom"},
            {"step": "eslint", "status": "SKIPPED", "detail": ""}, {"step": "browser E2E", "status": "NOT RUN", "detail": "needs chromium"}]
    assert verify.counts(rows) == "2 passed, 1 failed, 1 skipped, 1 not run"
    assert verify.tests_line(rows) == "django tests PASSED; pytest (dev_agent) FAILED; browser E2E NOT RUN"
    assert verify.tests_line([P("pyflakes")]).startswith("no automated test step")


def test_browser_e2e_is_always_stated():
    assert verify.e2e_line([P("django tests")]).startswith("Browser E2E: NOT PERFORMED (no UI files changed")
    got = verify.e2e_line([{"step": "browser E2E", "status": "NOT RUN", "detail": "chromium missing"}])
    assert "NOT RUN - chromium missing" in got and "NOT verified" in got
    assert verify.e2e_line([P("browser E2E")]) == "Browser E2E: PASSED"


def test_report_shows_counts_tests_and_e2e(repo, ctx):
    ctx.ledger.add_verification("final", [P("pyflakes"), {"step": "django tests", "status": "NOT RUN", "detail": "no test module is mapped"}])
    ctx.ledger.data["status"] = "completed"
    text = report.build(ctx.ledger)
    assert "Checks: 1 passed, 0 failed, 0 skipped, 1 not run" in text and "Automated tests: django tests NOT RUN" in text
    assert "Browser E2E: NOT PERFORMED" in text and "Overall: NOT VERIFIED (some checks did not run)" in text
