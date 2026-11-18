"""WealthFlow QA Module - AI code knowledge index (the source index behind the investigation tools).

No LLM is needed. From the real page and session: the sysadmin status endpoint reports a healthy index after a refresh,
the index refresh is incremental (second run parses nothing), and the live agent-step label of every new tool exists
in all four languages (en, ar, fr, de).
"""

_FETCH = """async ([url, method, body]) => {
  const res = await fetch(url, {method, headers: {"Content-Type": "application/json",
    "X-CSRFToken": (window.wfGetCsrfToken && window.wfGetCsrfToken()) || ""}, body: body ? JSON.stringify(body) : undefined});
  let data = null; try { data = await res.json(); } catch (e) {}
  return {status: res.status, data};
}"""

_URL = "/api/ai-platform/knowledge-index/"
_TOOLS = ["app_search", "app_symbol", "app_trace_calls", "app_trace_flow", "app_model_relations", "app_find_tests",
          "app_compare", "app_diagnose", "app_verify_fix", "app_index_status"]
_LANGS = ["en", "ar", "fr", "de"]


def _step(reporter, screenshot_logger, page, name, ok, detail, shot_name):
    shot = screenshot_logger.capture(page, "ai", shot_name, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "WealthFlow AI", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def _run(context, reporter, screenshot_logger):
    page = context.page
    context.goto_route("#ai")
    page.wait_for_selector("#ai-ws-input, #ai-chat-input", timeout=8000)

    first = page.evaluate(_FETCH, [_URL, "POST", {}])
    data = first["data"] or {}
    status = data.get("status") or {}
    ok = first["status"] == 200 and status.get("current") is True and status.get("state") == "ready" and (status.get("counts") or {}).get("symbols", 0) > 1000
    _step(reporter, screenshot_logger, page, "Code index refresh returns a current, ready index with symbols", ok,
          f"status={first['status']} state={status.get('state')} stale={status.get('stale_files')} counts={status.get('counts')}", "code_index_refresh")

    second = (page.evaluate(_FETCH, [_URL, "POST", {}])["data"] or {}).get("result") or {}
    _step(reporter, screenshot_logger, page, "A second refresh is incremental (nothing re-parsed, nothing rebuilt)",
          second.get("parsed") == 0 and second.get("rebuilt") is False, f"result={second}", "code_index_incremental")

    health = page.evaluate(_FETCH, [_URL, "GET", None])
    body = health["data"] or {}
    shape = {"version", "expected_version", "state", "counts", "stale_files", "current", "translations_missing"} <= set(body)
    _step(reporter, screenshot_logger, page, "Code index status endpoint reports version, state, counts, staleness and translation gaps",
          health["status"] == 200 and shape and body.get("version") == str(body.get("expected_version")), f"keys={sorted(body)}", "code_index_status")

    missing = []
    for lang in _LANGS:
        table = page.evaluate("async (l) => (await fetch(`/static/i18n/${l}.json`)).json()", lang)
        missing += [f"{lang}:{t}" for t in _TOOLS if f"ai_agent_tool_{t}" not in table]
    _step(reporter, screenshot_logger, page, "Live agent-step labels for the code investigation tools exist in en, ar, fr and de",
          not missing, f"missing={missing}", "code_index_labels")
    reporter.pages_visited.add("WealthFlow AI -> Code index")


def test_ai_code_index(context, reporter, screenshot_logger):
    try:
        _run(context, reporter, screenshot_logger)
    except Exception as ex:  # a failed check must be reported, not abort the rest of the suite
        shot = screenshot_logger.capture(context.page, "ai", "code_index", "error", "fail", "fail")
        reporter.add_step("AI code index", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot)
