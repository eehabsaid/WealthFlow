"""Browser contract for the out-of-domain refusal: the four locale files carry the refusal texts, each text names the domains with
the exact names the AI workspace shows, and the workspace's domain selector uses the same names. (No core.* imports: the E2E
runner has no Django. The refusal itself, the guide files and the model path are covered by the Django tests and the fake Ollama.)"""

_LANGS = ("en", "ar", "fr", "de")
_KEYS = ("ai_scope_no_info", "ai_scope_refused_business", "ai_scope_refused_app", "ai_scope_refused_locked")
_NAMES = ("ai_domain_business_data", "ai_domain_app_features")


def _run(context, reporter, screenshot_logger):
    page = context.page
    data = page.evaluate("""async (langs) => {
        const out = {};
        for (const l of langs) { const r = await fetch('/static/i18n/' + l + '.json'); out[l] = await r.json(); }
        return out;
    }""", list(_LANGS))
    problems = []
    for lang in _LANGS:
        table = data.get(lang) or {}
        for key in _KEYS + _NAMES:
            if not table.get(key):
                problems.append(f"{lang}:{key} missing")
        for key in _KEYS[1:]:
            text = table.get(key, "")
            if "{current}" not in text or "{other}" not in text:
                problems.append(f"{lang}:{key} lacks placeholders")
    context.goto_route("#ai")
    page.wait_for_selector("#ai-ws-input, #ai-chat-input", timeout=8000)
    shot = screenshot_logger.capture(page, "ai", "scope_refusal", "none", "view", "fail" if problems else "ok")
    reporter.add_step("AI out-of-domain refusal: i18n texts in en/ar/fr/de name the UI's domains", "WealthFlow AI",
                      "FAIL" if problems else "PASS", "; ".join(problems) or "all four locales carry the four refusal texts", screenshot_path=shot)


def test_ai_scope_refusal(context, reporter, screenshot_logger):
    try:
        _run(context, reporter, screenshot_logger)
    except Exception as ex:
        shot = screenshot_logger.capture(context.page, "ai", "scope_refusal_error", "none", "fail", "fail")
        reporter.add_step("AI out-of-domain refusal", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot)
    finally:
        context.goto_route("#ai")
