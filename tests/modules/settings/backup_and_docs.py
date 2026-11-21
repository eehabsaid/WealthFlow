"""Settings module phase 6: Portable Backup Archive download & Documentation Engine generation trigger. Split out of tests/modules/settings.py."""

from tests.core.download_verifier import verify_backup_archive, verify_downloaded_file
from tests.modules.settings.common import open_settings_tab, close_global_modal


def test_backup_and_docs(context, reporter, screenshot_logger):
    # 5. Portable Backup Archive Download
    open_settings_tab(context, "backup")

    try:
        with context.page.expect_download(timeout=5000) as download_info:
            context.page.evaluate("if (typeof triggerDownloadBackup === 'function') triggerDownloadBackup();")
        download = download_info.value
        save_path = f"test_downloads/{download.suggested_filename}"
        download.save_as(save_path)

        verify_downloaded_file(save_path, expected_extension=".wfbackup")
        table_count = verify_backup_archive(save_path)   # manifest, checksums, and every required table (budgets, permissions, login attempts...)
        shot_bk = screenshot_logger.capture(context.page, "settings", "backup", "none", "backup_download", "ok")
        reporter.exports_tested.append("Backup & Restore -> Create & Download Portable Backup (.wfbackup)")
        reporter.add_step("Backup Archive Download Verification", "Settings", "PASS", f"Verified backup archive: {save_path} ({table_count} tables, checksums OK, required tables present)", screenshot_path=shot_bk)
    except Exception as ex:
        reporter.add_step("Backup Archive Download", "Settings", "FAIL", f"Exception: {ex}")

    # 6. Documentation Engine Generation
    open_settings_tab(context, "documentation")

    try:
        context.page.evaluate("if (typeof handleGenerateClick === 'function') handleGenerateClick();")
        context.page.wait_for_timeout(1000)
        shot_doc = screenshot_logger.capture(context.page, "settings", "documentation", "doc_engine", "trigger", "ok")
        reporter.exports_tested.append("Documentation Engine -> Generate All Documents")
        reporter.add_step("Documentation Engine Generation Trigger", "Settings", "PASS", "Triggered doc engine document generation.", screenshot_path=shot_doc)
    except Exception as ex:
        reporter.add_step("Documentation Engine Trigger", "Settings", "FAIL", f"Exception: {ex}")

    try:   # the coding agent is not a web page, so it has no screenshot: its chapter comes from the content file (ai/doc_engine/extra_sections.py)
        import json
        from ai.doc_engine.config import CONTENT_FILE
        from ai.doc_engine.extra_sections import extra_nodes

        with open(CONTENT_FILE, encoding="utf-8") as handle:
            nodes = extra_nodes(json.load(handle))
        ok = len(nodes) == 1 and len(nodes[0].children) == 3
        reporter.add_step("Documentation Content: Coding Agent chapter", "Settings", "PASS" if ok else "FAIL", "Admin/technical guides carry the Coding Agent chapter with 3 parts." if ok else "Coding Agent chapter missing in the documentation content.")
    except Exception as ex:
        reporter.add_step("Documentation Content: Coding Agent chapter", "Settings", "FAIL", f"Exception: {ex}")

    # handleGenerateClick() can open the shared #globalModal ("Generation Validation Failed") and leave it up;
    # close it here so it does not block the next phase.
    close_global_modal(context.page)

    try:   # the documentation photographs each AI Advisor section on its own: exactly one section is visible at a time
        from tests.modules.settings.common import open_ai_section
        open_settings_tab(context, "ai-advisor")
        results = []
        for group in ("provider", "agent", "files"):
            open_ai_section(context.page, group)
            results.append(context.page.evaluate("() => [...document.querySelectorAll('[data-aia-group]')].filter(p => !p.hidden).map(p => p.dataset.aiaGroup)"))
        ok = results == [["provider"], ["agent"], ["files"]]
        reporter.add_step("Documentation Capture: AI Advisor sections", "Settings", "PASS" if ok else "FAIL", "Each AI Advisor section shows alone, so the capture photographs them one by one." if ok else f"Visible sections: {results}")
    except Exception as ex:
        reporter.add_step("Documentation Capture: AI Advisor sections", "Settings", "FAIL", f"Exception: {ex}")
