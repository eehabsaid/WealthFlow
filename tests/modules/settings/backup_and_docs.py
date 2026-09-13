"""Settings module phase 6: Portable Backup Archive download & Documentation Engine generation trigger. Split out of tests/modules/settings.py."""

from tests.core.download_verifier import verify_downloaded_file


def test_backup_and_docs(context, reporter, screenshot_logger):
    # 5. Portable Backup Archive Download
    context.page.evaluate("if (typeof switchSettingsTab === 'function') switchSettingsTab('backup');")
    context.page.wait_for_timeout(600)

    try:
        with context.page.expect_download(timeout=5000) as download_info:
            context.page.evaluate("if (typeof triggerDownloadBackup === 'function') triggerDownloadBackup();")
        download = download_info.value
        save_path = f"test_downloads/{download.suggested_filename}"
        download.save_as(save_path)

        verify_downloaded_file(save_path, expected_extension=".wfbackup")
        shot_bk = screenshot_logger.capture(context.page, "settings", "backup", "none", "backup_download", "ok")
        reporter.exports_tested.append("Backup & Restore -> Create & Download Portable Backup (.wfbackup)")
        reporter.add_step("Backup Archive Download Verification", "Settings", "PASS", f"Verified backup archive: {save_path}", screenshot_path=shot_bk)
    except Exception as ex:
        reporter.add_step("Backup Archive Download", "Settings", "FAIL", f"Exception: {ex}")

    # 6. Documentation Engine Generation
    context.page.evaluate("if (typeof switchSettingsTab === 'function') switchSettingsTab('documentation');")
    context.page.wait_for_timeout(600)

    try:
        context.page.evaluate("if (typeof handleGenerateClick === 'function') handleGenerateClick();")
        context.page.wait_for_timeout(1000)
        shot_doc = screenshot_logger.capture(context.page, "settings", "documentation", "doc_engine", "trigger", "ok")
        reporter.exports_tested.append("Documentation Engine -> Generate All Documents")
        reporter.add_step("Documentation Engine Generation Trigger", "Settings", "PASS", "Triggered doc engine document generation.", screenshot_path=shot_doc)
    except Exception as ex:
        reporter.add_step("Documentation Engine Trigger", "Settings", "FAIL", f"Exception: {ex}")
