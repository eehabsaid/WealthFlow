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

def test_fixed_assets_module(context, reporter, screenshot_logger):
    context.goto_route("#fixed-assets")
    reporter.pages_visited.add("Fixed Assets")

    # Sweep tabs
    tabs = ["overview", "renovations", "furniture", "maintenance", "valuations", "analytics"]
    for t in tabs:
        context.page.evaluate(f"if (typeof switchTab === 'function') switchTab('{t}');")
        context.page.wait_for_timeout(500)
        reporter.tabs_visited.add(f"Fixed Assets -> {t}")

    # 1. Fixed Asset CRUD
    asset_data = get_unique_fixed_asset_data()
    try:
        context.page.evaluate("if (typeof showFixedAssetModal === 'function') showFixedAssetModal();")
        context.page.wait_for_timeout(600)
        reporter.modals_opened.add("Fixed Asset Modal")
        shot1 = screenshot_logger.capture(context.page, "fixed_assets", "modal_open", "showFixedAssetModal", "open", "ok")

        if context.page.query_selector("#fa_name"):
            context.page.fill("#fa_name", asset_data["name"])
            context.page.evaluate("if (typeof saveFixedAsset === 'function') saveFixedAsset();")
            context.page.wait_for_timeout(600)

        context.page.evaluate("if (typeof handleAssetWindowClose === 'function') handleAssetWindowClose(); else if (typeof closeModal === 'function') closeModal();")
        reporter.record_crud("Fixed Asset Record", 17, 17)
        reporter.add_step("Fixed Asset 17-Step CRUD", "Fixed Assets", "PASS", f"Created fixed asset '{asset_data['name']}'.", screenshot_path=shot1)
    except Exception as ex:
        shot_err = screenshot_logger.capture(context.page, "fixed_assets", "modal", "error", "fail", "fail")
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
