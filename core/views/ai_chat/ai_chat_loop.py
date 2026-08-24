import json
import time
from core.services.ai.cache_manager import AICacheManager
from core.services.ai.tools import validate_and_execute_tool
from core.views.ai_chat.ai_chat_helpers import (
    MAX_TOOL_ITERATIONS,
    _tool_progress_label,
    _get_loop_timeout,
    _parse_tool_call,
    _fingerprint,
)


def run_tool_investigation_loop(provider, messages_seq, tools_param, tool_calls_req, content_str, user_text, user, conversation_id):
    """
    Runs the bounded multi-step tool investigation loop (up to MAX_TOOL_ITERATIONS)
    so the AI can chain tool calls in sequence — each step informed by the previous
    result — the same way a human investigator works.

    Pure code motion from AIChatView.post — same logic, same order of operations,
    just parametrized so it can live outside the view class.

    Returns (content_str, executed_tool_calls).
    """
    executed_tool_calls = []
    loop_start = time.monotonic()
    loop_timeout = _get_loop_timeout()
    seen_fingerprints: set[str] = set()

    # Progress cache for frontend polling
    cache_mgr = AICacheManager()
    progress_key = f"ai_loop_progress:{user.id}:{conversation_id}"
    iteration = 0
    while tool_calls_req and isinstance(tool_calls_req, list) and iteration < MAX_TOOL_ITERATIONS:
        # ── Wall-clock budget check ───────────────────────────────────────
        elapsed = time.monotonic() - loop_start
        if elapsed >= loop_timeout:
            messages_seq.append({
                "role": "system",
                "content": (
                    f"INVESTIGATION TIMEOUT: The total investigation budget of {loop_timeout}s was reached "
                    f"after {iteration} step(s). Provide your best answer using only the information "
                    "already gathered above. Do not call any further tools."
                ),
            })
            fallback_res = provider.generate(messages_seq, tools=None)
            if fallback_res.get("content"):
                content_str = fallback_res["content"]
            break

        iteration += 1
        tc = tool_calls_req[0]
        fn_name, fn_args = _parse_tool_call(tc)

        if not fn_name:
            # Malformed tool call — stop loop, use content already in content_str
            break

        # Auto-populate search_query for query_application_data if missing
        if fn_name == "query_application_data" and not fn_args.get("search_query"):
            fn_args["search_query"] = user_text

        # ── Repeat-call prevention ────────────────────────────────────────
        fp = _fingerprint(fn_name, fn_args)
        if fp in seen_fingerprints:
            messages_seq.append({
                "role": "system",
                "content": (
                    f"DUPLICATE TOOL CALL BLOCKED: You already called '{fn_name}' with these exact "
                    "arguments in a previous step. The result is already in the conversation above. "
                    "Use that existing result to answer the user's question, or call a different tool "
                    "to gather additional information."
                ),
            })
            # Count as one iteration to prevent infinite loops on this failure mode
            tool_calls_req = []
            # Ask the model to proceed — still offering tools so it can pivot to a different one
            next_res = provider.generate(messages_seq, tools=tools_param)
            content_str = next_res.get("content", content_str)
            tool_calls_req = next_res.get("tool_calls") or []
            continue

        seen_fingerprints.add(fp)

        # ── Publish progress state for frontend polling ───────────────────
        cache_mgr.set(
            progress_key,
            {
                "step": iteration,
                "max_steps": MAX_TOOL_ITERATIONS,
                "tool": fn_name,
                "label": _tool_progress_label(fn_name, fn_args),
                "status": "running",
                "elapsed_s": round(time.monotonic() - loop_start, 1),
            },
            ttl_seconds=120.0,
        )

        # ── Execute tool via existing validated pipeline ──────────────────
        audit_rec, tool_res = validate_and_execute_tool(fn_name, fn_args, user)
        audit_rec["step"] = iteration
        audit_rec["total_budget_elapsed_s"] = round(time.monotonic() - loop_start, 1)
        executed_tool_calls.append(audit_rec)

        # Append tool result to messages for the next model call
        tool_summary_str = json.dumps(tool_res, default=str)
        messages_seq.append(
            {
                "role": "system",
                "content": (
                    f"STEP {iteration}/{MAX_TOOL_ITERATIONS} — TOOL CALLED: '{fn_name}'\n"
                    f"TOOL EXECUTION RESULT: {tool_summary_str}\n\n"
                    f"If you have enough information to answer the user's query '{user_text}', "
                    "provide your final answer now. Otherwise, call the next most relevant tool."
                ),
            }
        )

        # ── Next model call — tools still offered ─────────────────────────
        next_res = provider.generate(messages_seq, tools=tools_param)
        if next_res.get("error"):
            # Provider error mid-loop — stop and use what we have
            break

        content_str = next_res.get("content", content_str)
        tool_calls_req = next_res.get("tool_calls") or []

    # ── Cap exhaustion fallback ───────────────────────────────────────────
    # If the loop exhausted MAX_TOOL_ITERATIONS without a text-only final answer
    if iteration >= MAX_TOOL_ITERATIONS and tool_calls_req:
        messages_seq.append({
            "role": "system",
            "content": (
                f"You have used the maximum number of investigation steps ({MAX_TOOL_ITERATIONS}). "
                "Provide your best answer using only the information already gathered above. "
                "Do not execute further tools."
            ),
        })
        final_res = provider.generate(messages_seq, tools=None)
        if final_res.get("content"):
            content_str = final_res["content"]

    # Clear progress state
    cache_mgr.set(
            progress_key,
            {"status": "done"},
            ttl_seconds=30.0,
        )

    return content_str, executed_tool_calls
