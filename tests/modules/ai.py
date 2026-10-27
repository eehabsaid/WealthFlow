"""
WealthFlow QA Module — WealthFlow AI Subsystem
Tests:
 1. Navigation to #ai route.
 2. Verify sidebar thread list, multiline textarea, and domain selector.
 3. Creating a new chat session.
 4. Capture module view screenshot.
 5. Answer feedback (thumbs) and Learned Answers modal (tests/modules/ai_learning.py).
 6. Instant answers for Budgets and Recurring transactions (tests/modules/ai_budgets.py).
 7. Downloadable answers: Excel / Word / PDF links in the chat, "export it" follow-ups, real downloads (tests/modules/ai_export.py).
 8. Net worth forecast answered from the wealth-growth projection, English and Arabic (tests/modules/ai_wealth.py).
 9. Agent mode: Ask/Agent switch, settings, live steps, Stop button (tests/modules/ai_agent.py).
10. Reasoning (thinking) setting: default, save, reload (tests/modules/ai_think_setting.py).
11. Agent progress + Stop shown while a document is written and after reopening a running chat (tests/modules/ai_progress_resume.py).
12. User guide as a styled HTML page (tests/modules/ai_guide_html.py).
13. Clean end-user workspace: no right panel, welcome cards or scan button (tests/modules/ai_workspace_clean.py).
14. Out-of-domain refusal texts in en/ar/fr/de name the UI's domains (tests/modules/ai_scope_refusal.py).
15. Ask hands a guide request to Agent mode and the mode bar follows (tests/modules/ai_mode_follow.py).
16. Guide files: numbered chapters, a page per chapter, short PDF contents (tests/modules/ai_guide_structure.py).
17. Agent reads screen data: the Cash Flow endpoint the tool wraps and the translated live step (tests/modules/ai_screen_data.py).
"""

from tests.modules.ai_budgets import test_ai_budgets
from tests.modules.ai_learning import test_ai_learning
from tests.modules.ai_export import test_ai_export
from tests.modules.ai_wealth import test_ai_wealth
from tests.modules.ai_agent import test_ai_agent
from tests.modules.ai_guide_html import test_ai_guide_html
from tests.modules.ai_guide_structure import test_ai_guide_structure
from tests.modules.ai_progress_resume import test_ai_progress_resume
from tests.modules.ai_think_setting import test_ai_think_setting
from tests.modules.ai_workspace_clean import test_ai_workspace_clean
from tests.modules.ai_scope_refusal import test_ai_scope_refusal
from tests.modules.ai_mode_follow import test_ai_mode_follow
from tests.modules.ai_screen_data import test_ai_screen_data


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

    test_ai_learning(context, reporter, screenshot_logger)
    test_ai_budgets(context, reporter, screenshot_logger)
    test_ai_export(context, reporter, screenshot_logger)
    test_ai_wealth(context, reporter, screenshot_logger)
    test_ai_agent(context, reporter, screenshot_logger)
    test_ai_think_setting(context, reporter, screenshot_logger)
    test_ai_progress_resume(context, reporter, screenshot_logger)
    test_ai_guide_html(context, reporter, screenshot_logger)
    test_ai_workspace_clean(context, reporter, screenshot_logger)
    test_ai_scope_refusal(context, reporter, screenshot_logger)
    test_ai_mode_follow(context, reporter, screenshot_logger)
    test_ai_guide_structure(context, reporter, screenshot_logger)
    test_ai_screen_data(context, reporter, screenshot_logger)
