"""Agent mode entry for AIChatView: when the user's chat switch is on "agent", the model investigates from the start."""

from core.services.ai.agent import agent_active
from core.services.ai.domains import APP
from core.services.ai.exports import ExportNoticeProvider
from core.services.ai.query_engine import verified_for_model
from core.views.ai_chat.chat_pipeline.agent_pipeline import run_agent_pipeline

from .generation_pipeline import build_provider_error_response
from .response_finalizer import finalize_success


def agent_stage(*, request, body, cache_mgr, progress_key, conversation, user_msg, user_text, route_text, trace, provider, export_formats, domain=""):
    """The agent's JsonResponse, or None when the request is not in Agent mode (the normal staged path then runs)."""
    if not agent_active(request.user, body.get("chat_mode")):
        return None
    previous = conversation.messages.filter(role="user", is_deleted=False).exclude(id=user_msg.id) \
        .order_by("-id").values_list("content", flat=True).first() or ""
    if export_formats:
        provider = ExportNoticeProvider(provider, [f.label for f in export_formats])
    return run_agent_pipeline(
        domain=domain, trace=trace, provider=provider, request=request, conversation=conversation, user_msg=user_msg, user_text=user_text,
        hint="" if domain == APP else verified_for_model(request.user, route_text, previous=previous) or "",
        respond=lambda content, calls, sources, extra=None: finalize_success(
            cache_mgr, progress_key, conversation, user_msg, user_text, content, calls, sources, request, extra=extra),
        on_error=lambda sources, err: build_provider_error_response(cache_mgr, progress_key, conversation, sources, user_msg, err))
