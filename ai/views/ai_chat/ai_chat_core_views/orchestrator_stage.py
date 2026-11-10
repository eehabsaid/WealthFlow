"""Multi-agent orchestrator branch of the chat request (off by default: Settings > AI Advisor)."""

from ai.models import AISetting
from ai.services.domains import APP
from ai.services.orchestration import Orchestrator

from ai.views.ai_chat.ai_chat_core_views.response_finalizer import finalize_success


def orchestrator_response(*, trace, provider, request, conversation, user_msg, user_text, cache_mgr, progress_key, domain):
    """The orchestrator's response when it is switched on (and the domain allows it), else None."""
    if AISetting.get("ai_multi_agent_enabled", "false", user=request.user).strip().lower() not in ("true", "1", "yes") or domain == APP:
        return None
    trace.skip_remaining("multi_agent_orchestrator")
    trace.log_summary()
    state = Orchestrator(provider).run(user_text, request.user)
    content_str = state.final_answer or "The orchestrator could not complete this task."
    sources = sorted({step["agent"] for step in state.steps})
    return finalize_success(cache_mgr, progress_key, conversation, user_msg, user_text, content_str, state.steps, sources, request)
