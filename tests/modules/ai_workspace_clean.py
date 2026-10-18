"""WealthFlow QA Module - the AI Workspace is for end users only.

Checks the real page: the right panel, the welcome status cards and every Autonomous Scan control are gone, the
end-user features stay, and the knowledge endpoint refuses changes from non-administrators.
"""

GONE_TEXT = ["Context Sources", "Tools Executed", "Confidence", "Application Modules", "Connected Provider", "Active Model",
             "Knowledge Entries", "AI Capabilities", "Autonomous Scan", "Run Autonomous"]
GONE = [".ai-ws-right", ".ai-ws-platform-card", "#ai-ws-chip-provider", "#ai-ws-chip-model", "#ai-ws-chip-knowledge", "#ai-ws-toggle-context"]
KEPT = ["#ai-ws-input", ".ai-ws-new-chat-btn", "#ai-ws-card-pinned-chats", "#ai-ws-card-saved-prompts", "#ai-ws-card-knowledge-search"]


def _step(reporter, screenshot_logger, page, name, ok, detail, shot_name):
    shot = screenshot_logger.capture(page, "ai", shot_name, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "WealthFlow AI", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def test_ai_workspace_clean(context, reporter, screenshot_logger):
    page = context.page
    context.goto_route("#ai")
    page.wait_for_selector("#ai-ws-input", timeout=8000)
    page.evaluate("() => { if (typeof _startNewAIChatConversation === 'function') _startNewAIChatConversation(); }")
    page.wait_for_selector(".ai-ws-empty-state", timeout=8000)
    body = page.inner_text("body").lower()
    found = [t for t in GONE_TEXT if t.lower() in body]
    present = [s for s in GONE if page.locator(s).count()]
    _step(reporter, screenshot_logger, page, "AI Workspace shows no right panel, status cards or scan text", not found and not present,
          f"text found={found} selectors found={present}", "workspace_clean")
    missing = [s for s in KEPT if not page.locator(s).count()]
    _step(reporter, screenshot_logger, page, "AI Workspace keeps chat, New Chat, Pinned Chats, Saved Prompts, Knowledge Search",
          not missing, f"missing={missing}", "workspace_kept")

    res = page.evaluate("""async () => {
      const r = await fetch("/api/ai-platform/knowledge/", {method: "POST", headers: {"Content-Type": "application/json",
        "X-CSRFToken": (window.wfGetCsrfToken && window.wfGetCsrfToken()) || ""}, body: JSON.stringify({action: "scan"})});
      return r.status; }""")
    ok = res in (400, 403)
    _step(reporter, screenshot_logger, page, "Knowledge endpoint no longer runs a scan (400 for admins, 403 for members)", ok,
          f"POST action=scan -> {res}", "scan_gone")
