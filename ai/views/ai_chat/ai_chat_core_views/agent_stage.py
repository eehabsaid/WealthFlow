"""Agent mode entry for AIChatView: when the user's chat switch is on "agent", the model investigates from the start."""

from ai.services.agent import agent_active
from ai.services.agent.redirect import moves_to_agent
from ai.services.domains import APP
from ai.services.exports import ExportNoticeProvider
from ai.services.exports.intent_model import restate_request
from ai.services.query_engine import verified_for_model
from ai.views.ai_chat.chat_pipeline.agent_pipeline import run_agent_pipeline

from ai.views.ai_chat.ai_chat_core_views.generation_pipeline import build_provider_error_response
from ai.views.ai_chat.ai_chat_core_views.response_finalizer import finalize_success


def agent_stage(*, request, body, cache_mgr, progress_key, conversation, user_msg, user_text, route_text, trace, provider, export_formats, domain="", allow_move=False):
    """The agent's JsonResponse, or None when the request is not in Agent mode (the normal staged path then runs).
    work_text: the complete request when the message is a follow-up (what the agent and the document writer work from; the chat keeps user_text).
    allow_move: the second call, made after the instant (0 model call) answers had their chance, lets Ask hand a guide request to Agent."""
    moved = {}
    active = agent_active(request.user, body.get("chat_mode"))
    if not active and not allow_move:
        return None
    # a file request: the model restates a follow-up ("where is the HTML file?") as the complete request, so the agent and the document writer
    # know what was asked earlier (the guide, its language); the chat keeps the message as typed
    work_text = restate_request(provider, user_text, conversation, user_msg, export_formats) if export_formats else user_text
    if not active:
        if not moves_to_agent(request.user, work_text, provider, domain):   # Ask mode cannot write a guide to the app: Agent mode does
            return None
        moved = {"chat_mode": "agent"}   # the chat's mode bar switches to Agent
    previous = conversation.messages.filter(role="user", is_deleted=False).exclude(id=user_msg.id) \
        .order_by("-id").values_list("content", flat=True).first() or ""
    if export_formats:
        provider = ExportNoticeProvider(provider, [f.label for f in export_formats])
    return run_agent_pipeline(
        domain=domain, trace=trace, provider=provider, request=request, conversation=conversation, user_msg=user_msg, user_text=work_text,
        hint="" if domain == APP else verified_for_model(request.user, route_text, previous=previous) or "",
        respond=lambda content, calls, sources, extra=None: finalize_success(
            cache_mgr, progress_key, conversation, user_msg, user_text, content, calls, sources, request, extra={**(extra or {}), **moved} or None),
        on_error=lambda sources, err: build_provider_error_response(cache_mgr, progress_key, conversation, sources, user_msg, err))
