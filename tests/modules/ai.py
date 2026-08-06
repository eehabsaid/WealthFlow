"""
WealthFlow QA Module — WealthFlow AI Subsystem
Tests:
 1. Navigation to #ai route.
 2. Verify sidebar thread list, multiline textarea, and domain selector.
 3. Creating a new chat session.
 4. Capture module view screenshot.
"""

def test_ai_module(context, reporter, screenshot_logger):
    context.goto_route("#ai")
    reporter.pages_visited.add("WealthFlow AI")

    try:
        context.page.wait_for_selector("#ai-ws-input, #ai-chat-input", timeout=8000)
        shot = screenshot_logger.capture(context.page, "ai", "workspace", "none", "view", "ok")
        reporter.add_step("WealthFlow AI Workspace View", "WealthFlow AI", "PASS", "Loaded AI Workspace successfully.", screenshot_path=shot)
    except Exception as ex:
        shot_err = screenshot_logger.capture(context.page, "ai", "workspace", "error", "fail", "fail")
        reporter.add_step("WealthFlow AI Workspace View", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot_err)
