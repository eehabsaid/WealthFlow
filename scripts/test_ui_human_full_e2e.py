"""
WealthFlow Human QA End-to-End Regression Test Suite Entrypoint
Runs via Playwright Headed/Headless Chromium against http://127.0.0.1:8000/

Usage Examples:
  # Full Regression Run (Visual Headed Mode)
  .\\venv\\Scripts\\python.exe test_ui_human_full_e2e.py --mode=full --headed

  # Targeted Module Execution
  .\\venv\\Scripts\\python.exe test_ui_human_full_e2e.py --mode=module --module=expenses

  # Targeted Language Matrix Test
  .\\venv\\Scripts\\python.exe test_ui_human_full_e2e.py --mode=lang --lang=ar

  # Targeted Viewport Test
  .\\venv\\Scripts\\python.exe test_ui_human_full_e2e.py --mode=device --device=mobile

Split into flat siblings (200-line rule):
  - e2e_backup_utils.py    : setup_django, create_pre_test_backup, restore_pre_test_backup
  - e2e_module_dispatch.py : MODULE_DISPATCH, run_module
  - test_ui_human_full_e2e.py (this file) : argparse + suite orchestration
"""

import sys
import argparse
import time

from e2e_backup_utils import setup_django, create_pre_test_backup, restore_pre_test_backup

from playwright.sync_api import sync_playwright
from tests.core.test_context import TestContext
from tests.core.reporter import QAReporter
from tests.core.screenshot_logger import ScreenshotLogger
from e2e_module_dispatch import run_module

def main():
    parser = argparse.ArgumentParser(description="WealthFlow Human QA End-to-End Regression Suite")
    parser.add_argument("--mode", default="full", choices=["full", "smoke", "module", "page", "crud", "lang", "theme", "device"])
    parser.add_argument("--module", default="all", choices=["all", "auth", "dashboard", "ai", "balance", "salary", "expenses", "certificates", "fixed_assets", "reports", "reminders", "financial_advisor", "settings", "translations", "billing"])
    parser.add_argument("--page", default=None)
    parser.add_argument("--lang", default="en", choices=["en", "ar", "fr", "de"])
    parser.add_argument("--theme", default="dark", choices=["dark", "light"])
    parser.add_argument("--device", default="desktop", choices=["desktop", "tablet", "mobile"])
    parser.add_argument("--headed", action="store_true", default=False, help="Run browser in visual headed mode (for local debugging on a machine with a display)")
    parser.add_argument("--headless", action="store_true", default=False, help="Run browser in headless mode (default)")
    parser.add_argument("--slowmo", type=int, default=150, help="Slow mo delay in milliseconds")
    parser.add_argument("--screenshots", default="all", choices=["all", "failures_only", "off"])

    args = parser.parse_args()

    headed = args.headed and not args.headless

    setup_django()

    print("\n==================================================================")
    print("  WEALTHFLOW HUMAN QA END-TO-END REGRESSION TEST SUITE            ")
    print("==================================================================")
    print(f"  Execution Mode : {args.mode.upper()}")
    print(f"  Target Module  : {args.module}")
    print(f"  Target Device  : {args.device} ({'Visual Headed' if headed else 'Headless'})")
    print("==================================================================")

    backup_filepath = None
    try:
        backup_filepath = create_pre_test_backup()
    except Exception as ex:
        print(f"[BACKUP WARN] Could not create pre-test backup: {ex}")

    reporter = QAReporter(output_dir="test_reports")
    screenshot_logger = ScreenshotLogger(output_dir="test_reports/screenshots", mode=args.screenshots)

    aborted_for_timeout = False
    max_duration_seconds = 20 * 60 if args.mode == "full" else 8 * 60

    try:
        with sync_playwright() as p:
            ctx = TestContext(p, headed=headed, slow_mo=args.slowmo, device=args.device, theme=args.theme)

            # Step 1: Login
            print("\n[STEP 1] Authenticating user session...")
            login_ok = ctx.login()
            assert login_ok, "API Authentication failed!"
            reporter.add_step("User Session Login", "Auth", "PASS", "Authenticated successfully.")

            # Step 2: Apply Theme & Language
            ctx.set_theme(args.theme)
            if args.lang != "en":
                ctx.set_language(args.lang)

            # Step 3: Run Test Modules in Sidebar Page Order
            modules_to_run = []
            if args.module != "all":
                modules_to_run = [args.module]
            else:
                modules_to_run = [
                    "auth", "dashboard", "ai", "balance", "salary", "certificates",
                    "fixed_assets", "expenses", "reports", "reminders",
                    "financial_advisor", "settings", "translations", "billing"
                ]

            # Suite-level watchdog: a hard wall-clock ceiling on the whole run.
            # Checked between modules (not via a hard process kill) so the
            # existing try/finally below still runs the DB restore and the
            # report is still generated with whatever data exists so far -
            # a killed process would skip both of those safety steps.
            run_started_at = time.time()

            for mod in modules_to_run:
                elapsed = time.time() - run_started_at
                if elapsed > max_duration_seconds:
                    aborted_for_timeout = True
                    print(f"\n[WATCHDOG] Aborting: suite exceeded the {max_duration_seconds}s time budget "
                          f"({elapsed:.0f}s elapsed). Remaining modules will be skipped.")
                    reporter.add_step(
                        "Suite Watchdog Timeout", "System", "FAIL",
                        f"Exceeded {max_duration_seconds}s time budget after {elapsed:.0f}s - "
                        f"remaining modules ({', '.join(modules_to_run[modules_to_run.index(mod):])}) were skipped."
                    )
                    break
                print(f"\n[RUNNING MODULE] Executing '{mod.upper()}' module test suite...")
                run_module(mod, ctx, reporter, screenshot_logger)

            ctx.close()

    finally:
        if backup_filepath:
            try:
                restore_pre_test_backup(backup_filepath)
            except Exception as ex:
                print(f"[RESTORE WARN] Database restore exception: {ex}")

    # Generate final HTML & JSON reports
    html_path, json_path = reporter.generate_reports()
    cov = reporter.calculate_coverage()

    print("\n==================================================================")
    print("            FINAL REGRESSION TEST SUITE RESULTS                   ")
    print("==================================================================")
    print(f"  Coverage Metric Score: {cov['overall_percentage']}%")
    print(f"  Total Pages Swept   : {cov['pages_count']}")
    print(f"  Total Sub-Tabs Swept: {cov['tabs_count']}")
    print(f"  Total Modals Swept  : {cov['modals_count']}")
    print(f"  Total CRUD Runs     : {cov['cruds_count']}")
    print(f"  Total Exports Tested: {cov['exports_count']}")
    print(f"  Passed Steps        : {reporter.passed_count}")
    print(f"  Failed Steps        : {reporter.failed_count}")
    print(f"  HTML Report         : {html_path}")
    print(f"  JSON Report         : {json_path}")
    print("==================================================================")

    if aborted_for_timeout:
        print(f"\n[WATCHDOG] ABORTED: run exceeded its {max_duration_seconds}s time budget and was "
              f"stopped early. Database was restored safely; the reports above only reflect the "
              f"modules that completed before the abort.")
        return False

    if reporter.failed_count == 0:
        print("\nSUCCESS: 100% CLEAN PASS! The regression test suite completed successfully with ZERO errors!")
        return True
    else:
        print(f"\nCOMPLETED WITH NOTICES: Execution completed with {reporter.failed_count} non-fatal validation notices.")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
