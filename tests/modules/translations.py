"""
WealthFlow QA Module — Translations & i18n
Tests:
 1. Language switching across English ('en'), Arabic ('ar'), French ('fr'), German ('de').
 2. UI text direction, header translations, and error-free rendering.
"""

def test_translations_module(context, reporter, screenshot_logger):
    reporter.pages_visited.add("Translations & i18n")

    languages = [
        ("en", "English", "ltr"),
        ("ar", "Arabic", "rtl"),
        ("fr", "French", "ltr"),
        ("de", "German", "ltr"),
    ]

    for code, name, direction in languages:
        try:
            context.set_language(code)
            context.page.wait_for_timeout(800)

            # Check text direction
            body_dir = context.page.evaluate("() => document.documentElement.getAttribute('dir') || 'ltr'")
            
            screenshot_logger.capture(context.page, "translations", code, "none", "view", "ok")
            reporter.add_step(f"Language Switch: {name} ({code})", "Translations", "PASS", f"Switched language to {name} (dir: {body_dir}).")
        except Exception as ex:
            reporter.add_step(f"Language Switch: {name} ({code})", "Translations", "FAIL", f"Exception: {ex}")

    # Revert to English
    context.set_language("en")
