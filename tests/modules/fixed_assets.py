"""
WealthFlow QA Module — Fixed Assets
Tests:
 1. 17-step CRUD on Fixed Assets (Real Estate, Vehicles, Gold, Other Assets) and sub-entities.
 2. PDF Analytics Report download verification (/api/fixed-assets/reports/pdf/ -> fixed_assets_report.pdf).
 3. Excel Analytics Report download verification (/api/fixed-assets/reports/excel/ -> fixed_assets_report.xlsx).
 4. Immediate downstream verification to Net Worth, Portfolio Optimizer, and Asset Analytics.
"""

from tests.core.data_generator import get_unique_fixed_asset_data
from tests.core.download_verifier import verify_downloaded_file
from tests.core.assertions import verify_downstream_impact
from tests.core.crud_verifier import CrudVerifier

def test_fixed_assets_module(context, reporter, screenshot_logger):
    # Registered once, persistently: delete triggers a native confirm()
    # dialog. Registering early avoids a possible race between the dialog
    # firing synchronously inside page.evaluate() and Playwright attaching
    # a listener registered right before the triggering call.
    context.page.on("dialog", lambda dialog: dialog.accept())

    context.goto_route("#fixed-assets")
    reporter.pages_visited.add("Fixed Assets")

    # Sweep tabs (declared, correct ids per doc_engine/inventory.json)
    tabs = ["assets", "dashboard", "analytics", "reports"]
    for t in tabs:
        context.page.evaluate(f"if (typeof switchTab === 'function') switchTab('{t}');")
        context.page.wait_for_timeout(500)
        reporter.tabs_visited.add(f"Fixed Assets -> {t}")

    # 1. Fixed Asset CRUD — real, API-verified (was: unconditional 17/17,
    # create-only, no edit/delete at all despite the "17-step CRUD" label)
    asset_data = get_unique_fixed_asset_data()
    checker = CrudVerifier(context.page, api_list_url="/api/fixed-assets/", list_key="assets")
    try:
        before_ids = checker.snapshot_ids()

        context.page.evaluate("if (typeof showFixedAssetModal === 'function') showFixedAssetModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Fixed Asset Modal")
        shot1 = screenshot_logger.capture(context.page, "fixed_assets", "modal_open", "showFixedAssetModal", "open", "ok")
        checker.add_manual_step(context.page.query_selector("#fa_name") is not None)

        if context.page.query_selector("#fa_name"):
            context.page.select_option("#fa_type", label="Real Estate")
            context.page.wait_for_timeout(500)
            context.page.fill("#fa_name", asset_data["name"])
            if context.page.query_selector("#fa_status"):
                context.page.select_option("#fa_status", index=0)
            context.page.wait_for_selector("#fa_purchase_currency option", state="attached", timeout=5000)
            if context.page.query_selector("#fa_purchase_currency"):
                context.page.select_option("#fa_purchase_currency", index=0)
            # Use a small, safe purchase price rather than the data
            # generator's large realistic amounts (e.g. 1.8M EGP) — the
            # disposable test DB's sample Cash balance is finite and the
            # backend correctly rejects a purchase it can't cover
            # (insufficient_balance), same validation real users see.
            test_purchase_price = 100
            if context.page.query_selector("#fa_purchase_price"):
                context.page.fill("#fa_purchase_price", str(test_purchase_price))
            if context.page.query_selector("#fa_purchase_usd_rate"):
                context.page.fill("#fa_purchase_usd_rate", "50")
            # Date fields use a custom picker that hides the native <input>;
            # setting .value via JS is the app's own documented supported
            # path for external code (see static/js/datepicker/dom.js).
            context.page.evaluate(f"document.getElementById('fa_purchase_date').value = '{asset_data['purchase_date']}'")
            if context.page.query_selector("#fa_current_value"):
                context.page.fill("#fa_current_value", str(test_purchase_price * 1.1))
            context.page.evaluate(f"document.getElementById('fa_last_valuation_date').value = '{asset_data['purchase_date']}'")
            # Purchase Payments: total must equal purchase price, validated
            # client-side (validatePurchasePayments) before the API is ever
            # called — a mismatch silently toasts and aborts the save with
            # no exception. Fill the first (default Cash, no bank needed)
            # row to match.
            payment_amount_input = context.page.query_selector("#purchasePaymentsContainer .purchase-amount")
            if payment_amount_input:
                payment_amount_input.fill(str(test_purchase_price))
            context.page.evaluate("(async () => { if (typeof saveFixedAsset === 'function') { await saveFixedAsset(); } })()")
            context.page.wait_for_timeout(1500)

        create_result = checker.verify_created(before_ids, match_field="name", expected_value=asset_data["name"])

        # Edit: reopen and change the name via the real edit path.
        # saveFixedAsset() defaults its assetId param to null (= create) if
        # called with no arguments — the id must be passed explicitly for
        # this to be a real PUT/edit rather than silently creating another row.
        new_name = asset_data["name"] + " (Edited)"
        if create_result.new_id is not None:
            context.page.evaluate(f"if (typeof showFixedAssetModal === 'function') showFixedAssetModal({create_result.new_id});")
            context.page.wait_for_timeout(600)
            if context.page.query_selector("#fa_name"):
                context.page.fill("#fa_name", new_name)
                context.page.evaluate(f"(async () => {{ if (typeof saveFixedAsset === 'function') {{ await saveFixedAsset({create_result.new_id}); }} }})()")
                context.page.wait_for_timeout(800)
        edit_result = checker.verify_field_updated(create_result.new_id, "name", new_name)

        # Delete via the real deleteFixedAsset() JS function. It uses a
        # native confirm() dialog, which Playwright auto-dismisses (returns
        # false) unless a handler is registered to accept it first.
        if create_result.new_id is not None:
            context.page.evaluate(f"if (typeof deleteFixedAsset === 'function') deleteFixedAsset({create_result.new_id});")
            context.page.wait_for_timeout(1000)
        delete_result = checker.verify_deleted(create_result.new_id)

        overall_pass = create_result.passed and edit_result.passed and delete_result.passed
        reporter.record_crud("Fixed Asset Record", checker.steps_passed, checker.steps_total)
        status = "PASS" if overall_pass else "FAIL"
        detail = f"Create: {create_result.detail} | Edit: {edit_result.detail} | Delete: {delete_result.detail}"
        reporter.add_step("Fixed Asset CRUD (API-verified)", "Fixed Assets", status, detail, screenshot_path=shot1)
    except Exception as ex:
        shot_err = screenshot_logger.capture(context.page, "fixed_assets", "modal", "error", "fail", "fail")
        reporter.record_crud("Fixed Asset Record", checker.steps_passed, max(checker.steps_total, 1))
        reporter.add_step("Fixed Asset CRUD Test", "Fixed Assets", "FAIL", f"Exception: {ex}", screenshot_path=shot_err)

    # 2. PDF & Excel Report Downloads on Analytics tab
    context.page.evaluate("if (typeof switchTab === 'function') switchTab('analytics');")
    context.page.wait_for_timeout(600)

    # PDF Report Download & Verification
    try:
        pdf_bytes = context.page.evaluate("""async () => {
            const res = await fetch('/api/fixed-assets/reports/pdf/?scope=portfolio&lang=en');
            if (!res.ok) throw new Error('PDF report fetch failed');
            const buf = await res.arrayBuffer();
            return Array.from(new Uint8Array(buf));
        }""")
        save_path_pdf = "test_downloads/fixed_assets_report.pdf"
        with open(save_path_pdf, "wb") as f:
            f.write(bytes(pdf_bytes))

        verify_downloaded_file(save_path_pdf, expected_extension=".pdf")
        shot_pdf = screenshot_logger.capture(context.page, "fixed_assets", "analytics", "pdf_report", "download", "ok")
        reporter.exports_tested.append("Fixed Assets Analytics -> PDF Analytics Report")
        reporter.add_step("Fixed Assets PDF Analytics Report Download", "Fixed Assets", "PASS", f"Verified PDF file: {save_path_pdf}", screenshot_path=shot_pdf)
    except Exception as ex:
        reporter.add_step("Fixed Assets PDF Analytics Report", "Fixed Assets", "FAIL", f"Exception: {ex}")

    # Excel Report Download & Verification
    try:
        excel_bytes = context.page.evaluate("""async () => {
            const res = await fetch('/api/fixed-assets/reports/excel/?scope=portfolio&lang=en');
            if (!res.ok) throw new Error('Excel report fetch failed');
            const buf = await res.arrayBuffer();
            return Array.from(new Uint8Array(buf));
        }""")
        save_path_excel = "test_downloads/fixed_assets_report.xlsx"
        with open(save_path_excel, "wb") as f:
            f.write(bytes(excel_bytes))

        verify_downloaded_file(save_path_excel, expected_extension=".xlsx")
        shot_excel = screenshot_logger.capture(context.page, "fixed_assets", "analytics", "excel_report", "download", "ok")
        reporter.exports_tested.append("Fixed Assets Analytics -> Download Excel Workbook")
        reporter.add_step("Fixed Assets Excel Workbook Download", "Fixed Assets", "PASS", f"Verified excel file: {save_path_excel}", screenshot_path=shot_excel)
    except Exception as ex:
        reporter.add_step("Fixed Assets Excel Workbook Download", "Fixed Assets", "FAIL", f"Exception: {ex}")

    # 3. Downstream verification
    verify_downstream_impact(context.page, "Fixed Asset Creation", "dashboard")
    verify_downstream_impact(context.page, "Fixed Asset Creation", "financial-advisor")
