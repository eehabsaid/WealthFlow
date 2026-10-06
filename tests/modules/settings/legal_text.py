"""Settings module phase: Legal Text tab (sysadmin-only editor for Privacy / Terms).

Non-destructive for a local database: the publish step re-publishes the CURRENT text unchanged under a
throwaway version label (round trip), so the wording users see never changes; only the version label and
the history gain a row. Re-consent is left OFF so no account is prompted.
"""

from tests.modules.settings.common import open_settings_tab, _uid


def _step(reporter, screenshot_logger, page, name, ok, detail, tab):
    shot = screenshot_logger.capture(page, "settings", tab, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "Settings", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def test_legal_text(context, reporter, screenshot_logger):
    page = context.page
    try:
        opened = open_settings_tab(context, "legal", wait_ms=1500)
        editor = page.locator(".legal-editor").count() == 1
        reporter.tabs_visited.add("Settings -> legal")
        _step(reporter, screenshot_logger, page, "Legal Text tab opens for the sysadmin", opened and editor,
              f"hash={page.evaluate('location.hash')} editor={editor}", "legal_text_open")

        # Editing one section updates only the in-memory edit state until published.
        before = page.evaluate("_legalState.payload.versions.length")
        title_ok = page.locator(".legal-edit-section").count() >= 1
        page.select_option("#legalLangSelect", "ar")
        page.wait_for_timeout(300)
        rtl = page.evaluate("document.querySelector('.legal-edit-title').getAttribute('dir')") == "rtl"
        page.select_option("#legalLangSelect", "en")
        page.wait_for_timeout(300)
        _step(reporter, screenshot_logger, page, "Legal editor lists sections and switches language (Arabic is RTL)",
              title_ok and rtl, f"sections_present={title_ok} ar_rtl={rtl}", "legal_text_lang")

        # Round-trip publish: same text, new label.
        label = f"e2e-{_uid()}"
        _read = (
            "fetch('/terms/').then(r => r.text()).then(html => { const d = new DOMParser().parseFromString(html, 'text/html');"
            " return {label: (d.querySelector('.legal-meta bdi') || {}).textContent || '',"
            " body: [...d.querySelectorAll('#legalMain h1, #legalMain h2, #legalMain section p, #legalMain h2 ~ p')]"
            ".map(n => n.textContent.trim()).join('|')}; })"
        )
        terms_before = page.evaluate(_read)
        page.fill("#legalNewLabel", label)
        # The app uses smooth scrolling, so Playwright's own scroll-into-view can report "outside of the
        # viewport"; jump instantly first.
        page.locator("#legalPublishBtn").evaluate("el => el.scrollIntoView({block: 'center', behavior: 'instant'})")
        page.click("#legalPublishBtn")
        page.wait_for_timeout(1800)
        history = page.evaluate("_legalState.payload.versions.map(v => v.label)")
        published = bool(history) and history[0] == label and len(history) == before + 1
        terms_after = page.evaluate(_read)
        same_text = bool(terms_before["body"]) and terms_before["body"] == terms_after["body"]
        _step(reporter, screenshot_logger, page, "Publishing a new version adds history and keeps the wording",
              published and same_text and terms_after["label"] == label,
              f"history_top={history[:1]} rows={len(history)} same_text={same_text}", "legal_text_publish")

        dup = page.evaluate(
            "fetch('/api/settings/legal/', {method:'POST', headers:{'Content-Type':'application/json',"
            "'X-CSRFToken': (document.cookie.match(/csrftoken=([^;]+)/)||[])[1]||''},"
            f"body: JSON.stringify({{label:'{label}', content:{{}}}})}}).then(r => r.status)"
        )
        bad = page.evaluate(
            "fetch('/api/settings/legal/', {method:'POST', headers:{'Content-Type':'application/json',"
            "'X-CSRFToken': (document.cookie.match(/csrftoken=([^;]+)/)||[])[1]||''},"
            "body: JSON.stringify({label:'bad label!', content:{}})}).then(r => r.status)"
        )
        _step(reporter, screenshot_logger, page, "Legal publish rejects a duplicate and an invalid label",
              dup == 409 and bad == 400, f"duplicate={dup} invalid={bad}", "legal_text_validation")
    except Exception as ex:
        shot = screenshot_logger.capture(page, "settings", "legal_text_error", "none", "fail", "fail")
        reporter.add_step("Legal Text settings", "Settings", "FAIL", f"Exception: {ex}", screenshot_path=shot)
