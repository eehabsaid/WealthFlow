"""Reasoning path for how / where / should questions about using the app.

No data snapshot and no tools. The model gets a small prompt: the best few knowledge chunks (generated
data-flows file, page descriptions, docstrings), the user's own approved answers to similar questions, and a
tiny slice of the user's setup, and is told to weigh the options and state what is uncertain. One LLM call,
bounded by a timeout and a token cap; every step is traced on the [AI-PIPELINE] log.

If the model fails or returns nothing (slow hardware), the user still gets the retrieved facts, labelled as
retrieval-only (source "knowledge_fallback": never stored as a learnable example), and the next 30 minutes
use a compact budget for that model (see app_knowledge/budget.py).
"""

from __future__ import annotations

from typing import Any, Callable

from core.models import AppSettings
from core.services.ai import app_knowledge as ak
from core.services.ai.app_knowledge import budget as bud
from core.views.ai_chat.ai_chat_helpers import _aiT_fallback_no_answer

from .trace import PipelineTrace, TracedProvider

DEFAULT_MAX_TOKENS, DEFAULT_TIMEOUT_S = 320, 300
FALLBACK_SOURCE = "knowledge_fallback"


def _flag(user, key: str, default: str = "true") -> bool:
    return str(AppSettings.get(key, default, user=user)).strip().lower() not in ("false", "0", "no", "off")


def _int(user, key: str, default: int) -> int:
    try:
        return max(1, int(AppSettings.get(key, str(default), user=user)))
    except (TypeError, ValueError):
        return default


def workflow_enabled(user) -> bool:
    return _flag(user, "ai_workflow_reasoning")


def run_workflow_pipeline(*, trace: PipelineTrace, provider, request, conversation, user_msg, user_text: str,
                          respond: Callable[..., Any], on_error: Callable[[list, str], Any]):
    model = str(getattr(provider, "model", "") or "")
    provider = TracedProvider(provider, trace)
    user = request.user
    budget = bud.choose(model, _int(user, "ai_workflow_max_tokens", DEFAULT_MAX_TOKENS),
                        _int(user, "ai_workflow_timeout_s", DEFAULT_TIMEOUT_S))
    try:
        with trace.stage("knowledge") as rec:
            ranked = ak.retrieve_knowledge(user_text, budget.max_chunks, budget.max_chars)
            examples = ak.find_examples(user, user_text)
            data_slice = ak.build_data_slice(user)
            rec.detail.update({
                "chunks": [{"id": c["id"], "score": round(s, 2)} for s, c in ranked],
                "chunk_chars": sum(len(c["text"]) for _, c in ranked), "examples": len(examples),
                "slice_chars": len(data_slice), "budget": budget.name,
            })
        chunks = [c for _, c in ranked]
        trace.skip("retrieve", "workflow_path")
        trace.skip("prefetch", "workflow_path")
        history = []
        if budget.history_messages:
            qs = conversation.messages.filter(is_deleted=False).exclude(id=user_msg.id).order_by("-id")
            history = list(qs[:budget.history_messages])[::-1]
        messages = ak.build_messages(user_text, chunks, examples, data_slice, history)

        with trace.stage("reason") as rec:
            res = provider.generate(messages, tools=None, max_tokens=budget.max_tokens, temperature=0.2, timeout=budget.timeout_s)
            res = res if isinstance(res, dict) else {}
            error, content = res.get("error"), str(res.get("content") or "").strip()
            rec.detail.update({"mode": "workflow", "budget": budget.name, "prompt_chars": sum(len(m["content"]) for m in messages),
                               "content_chars": len(content), "error": error})
        trace.skip("tool", "provider_error" if error else "workflow_path_no_tools")
        trace.skip("validate", "provider_error" if error else "workflow_path_no_figures")

        debug = str(AppSettings.get("ai_pipeline_debug", "false", user=user)).strip().lower() in ("true", "1", "yes")
        extra = {"pipeline": trace.to_dict()} if debug else None
        if content and not error:
            bud.clear_slow(model)
            sources = [ak.SOURCE_MARK]
            path = "model"
        else:
            if error:
                bud.mark_slow(model)
            if not chunks:   # nothing to fall back on
                with trace.stage("respond") as rec:
                    rec.detail["path"] = "provider_error"
                    return on_error([ak.SOURCE_MARK], str(error or "empty model reply"))
            content, sources, path = ak.fallback_text(user_text, chunks), [FALLBACK_SOURCE], "retrieval_fallback"
        with trace.stage("respond") as rec:
            rec.detail.update({"path": path, "content_chars": len(content), "sources": sources})
            return respond(content or _aiT_fallback_no_answer(), [], sources, extra)
    finally:
        trace.log_summary()
