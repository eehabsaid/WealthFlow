"""AI Financial Advisor — core chat endpoint (AIChatView).

Package layout (the 200-line-per-file convention):
- conversation_setup.py    conversation lookup, progress-cache bootstrap
- export_stage.py          "export it to Excel" follow-ups (previous answer -> file)
- generation_pipeline.py   context assembly, provider-generation + retry
- response_finalizer.py    persistence, knowledge extraction, response build

The default path runs through the staged pipeline in core/views/ai_chat/chat_pipeline/
(Understand -> Retrieve -> Reason -> Tool -> Validate -> Respond). `get_active_ai_provider` is invoked
here (not in a sibling) so the test patch target `...ai_chat_core_views.get_active_ai_provider` resolves.
"""

import json

from django.http import JsonResponse
from django.views import View

from core.validators.json_body import parse_json_body
from core.integrations.ai_provider import get_active_ai_provider
from core.models import AppSettings
from core.services.ai.cache_manager import AICacheManager
from core.services.ai.direct_answers import try_direct_answer
from core.services.ai.domains import APP, BUSINESS, app_enabled, resolve_domain
from core.services.ai.exports import ExportNoticeProvider, requested as detect_export_formats, strip_export_terms
from core.services.ai.query_engine import verified_for_model
from core.services.ai.orchestration import Orchestrator
from core.services.ai.usage import MeteredProvider, TokenMeter, limit_status
from core.views.ai_chat.ai_chat_helpers import _api_auth_required
from core.services.ai.app_knowledge import is_workflow_question
from core.views.ai_chat.chat_pipeline import (ESCALATE, PipelineTrace, escalating, run_default_pipeline, run_investigator_pipeline,
                                              run_workflow_pipeline, should_go_direct, understand, workflow_enabled)
from core.views.ai_chat.chat_pipeline.trace import log_request_start

from .agent_stage import agent_stage
from .conversation_setup import (
    build_provider_disabled_response,
    build_token_limit_response,
    init_progress,
    resolve_conversation,
    save_user_message,
)
from .export_stage import export_followup_response
from .generation_pipeline import build_provider_error_response
from .response_finalizer import finalize_success

__all__ = ["AIChatView"]


class AIChatView(View):
    """Endpoint for sending messages to AI Financial Advisor. URL: POST /api/financial-advisor/ai/chat/

    Order: export follow-up -> Agent mode (chat switch "agent": the model owns the tool loop) -> instant answers ->
    investigator / workflow / default staged pipeline. The user always receives a text answer; never a hang or silent failure.
    """

    def post(self, request):
        log_request_start(getattr(request.user, "id", None), len(request.body or b""))
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        try:
            body = parse_json_body(request)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        user_text = str(body.get("message", "")).strip()
        if not user_text:
            return JsonResponse({"error": "Message text cannot be empty"}, status=400)

        conversation = resolve_conversation(request, body, user_text)

        # MANDATORY REQUIREMENT: Always save user message to history FIRST
        user_msg = save_user_message(conversation, user_text)

        # Publish initial running state immediately so polling sees progress right away
        cache_mgr = AICacheManager()
        progress_key = init_progress(cache_mgr, request, conversation)

        # Stage 1 — Understand (deterministic, no LLM): runs before anything else
        trace = PipelineTrace(request.user.id, conversation.id)
        with trace.stage("understand") as rec:
            # the sysadmin's allowed chat domains win over what the browser sent (Settings > AI Advisor > Chat domains)
            chosen = resolve_domain(str(body.get("question_domain", "")))   # "" = none chosen and both allowed: inferred
            # Strict rules (tools, context, knowledge paths): the App domain, and Business when the sysadmin switched the App domain off.
            # Business chosen while both are allowed keeps the usual paths (how-do-I-record-it answers use the app knowledge).
            domain = chosen if chosen == APP or (chosen == BUSINESS and not app_enabled()) else ""
            understanding = understand(user_text, chosen)
            understanding.enforced = domain
            rec.detail.update(understanding.to_dict())

        # Check if AI provider is active
        provider = get_active_ai_provider(user=request.user)
        if not provider:
            trace.skip_remaining("provider_disabled")
            trace.log_summary()
            return build_provider_disabled_response(cache_mgr, progress_key, conversation, user_msg)

        # Monthly token limit: applies only to users on the general AI settings (own settings = unlimited)
        usage = limit_status(request.user)
        if usage["exceeded"]:
            trace.skip_remaining("token_limit")
            trace.log_summary()
            return build_token_limit_response(cache_mgr, progress_key, conversation, user_msg, usage)
        request._ai_token_meter = TokenMeter()
        provider = MeteredProvider(provider, request._ai_token_meter)

        # Stage 1a — Export follow-up ("export it to Excel"): see export_stage.py. Data questions that also ask for a file
        # are answered normally and finalize_success attaches the links to their own answer.
        export_formats = detect_export_formats(user_text)
        route_text = strip_export_terms(user_text) if export_formats else user_text  # the router sees the question only
        if export_formats:
            followup = export_followup_response(cache_mgr=cache_mgr, progress_key=progress_key, conversation=conversation, user_msg=user_msg,
                                                user_text=user_text, route_text=route_text, understanding=understanding, request=request, trace=trace)
            if followup is not None:
                return followup

        # Stage 1a' — Agent mode (per-user Ask/Agent switch): the model investigates with tools from the first call.
        agent_response = agent_stage(request=request, body=body, cache_mgr=cache_mgr, progress_key=progress_key, conversation=conversation,
                                     user_msg=user_msg, user_text=user_text, route_text=route_text, trace=trace, provider=provider,
                                     export_formats=export_formats, domain=domain)
        if agent_response is not None:
            return agent_response

        # Stage 1b — Route: the query engine answers supported data questions with 0 LLM calls (1 short
        # slot-filling call only if unclear). Runs BEFORE the orchestrator branch so multi-agent can
        # never hijack a fast question. Every decision is traced on the `route` stage.
        info = {}
        with trace.stage("route") as rec:
            # the previous user message lets a short follow-up ("and how much do I hold?") inherit its topic
            previous = conversation.messages.filter(role="user", is_deleted=False).exclude(id=user_msg.id) \
                .order_by("-id").values_list("content", flat=True).first() or ""
            direct = None if domain == APP else try_direct_answer(request.user, route_text, provider=provider, understanding=understanding,
                                       info=info, elapsed_ms=trace.elapsed_ms(), previous=previous, force=bool(export_formats))
            rec.detail.update(info)
            rec.detail["llm_calls"] = info.get("llm_calls", 0)
        if direct:
            trace.skip_remaining("direct_answer")
            trace.log_summary()
            return finalize_success(
                cache_mgr, progress_key, conversation, user_msg, user_text,
                direct["content"], direct["tool_calls"], direct["sources"], request,
            )
        verified_data = None
        if not direct and domain != APP:   # the App domain never sees the user's data, computed or not
            # Direct Answers OFF (or no instant answer): the model still gets the exact computed rows, never just a summary
            verified_data = verified_for_model(request.user, route_text, previous=previous, info=info)
            rec_route = trace.records.get("route")
            if rec_route is not None and info.get("verified_data"):
                rec_route.detail["verified_data"] = info["verified_data"]
        facts_request = info.get("facts_request")
        if export_formats:
            # every later model-calling path goes through `provider`, so one proxy tells the model the app attaches the files
            provider = ExportNoticeProvider(provider, [f.label for f in export_formats])

        respond = lambda content, calls, sources, extra=None: finalize_success(  # noqa: E731
            cache_mgr, progress_key, conversation, user_msg, user_text, content, calls, sources, request, extra=extra,
        )
        on_error = lambda sources, err: build_provider_error_response(  # noqa: E731
            cache_mgr, progress_key, conversation, sources, user_msg, err
        )
        investigate = lambda why: run_investigator_pipeline(  # noqa: E731
            trace=trace, provider=provider, request=request, conversation=conversation, user_msg=user_msg,
            user_text=user_text, respond=respond, on_error=on_error, why=why, domain=domain,
        )

        # Stage 1c — the investigator: code questions (sysadmin) or mode "always" go straight to a tool-using
        # exploration of the whole app; in mode "auto" it takes over below when a normal path gives up.
        direct_why = should_go_direct(request.user, user_text, computed=bool(verified_data), domain=domain)
        if direct_why:
            return investigate(direct_why)
        esc_respond, esc_on_error, esc_box = escalating(request.user, respond, on_error)

        # Stage 1d — how / where / should questions about using the app: reason from retrieved app
        # knowledge (no data snapshot, no tools). Advice questions with computed facts keep the data path.
        if not facts_request and domain != BUSINESS and workflow_enabled(request.user) and is_workflow_question(user_text):
            result = run_workflow_pipeline(
                trace=trace, provider=provider, request=request, conversation=conversation, user_msg=user_msg,
                user_text=user_text, respond=esc_respond, on_error=esc_on_error,
            )
            return investigate(esc_box.get("why", "escalation")) if result is ESCALATE else result

        multi_agent_str = AppSettings.get("ai_multi_agent_enabled", "false", user=request.user).strip().lower()
        if multi_agent_str in ("true", "1", "yes") and domain != APP:
            trace.skip_remaining("multi_agent_orchestrator")
            trace.log_summary()
            orchestrator = Orchestrator(provider)
            state = orchestrator.run(user_text, request.user)
            content_str = state.final_answer or "The orchestrator could not complete this task."
            sources = sorted({step["agent"] for step in state.steps})
            return finalize_success(
                cache_mgr, progress_key, conversation, user_msg, user_text,
                content_str, state.steps, sources, request,
            )

        # Stages 2-6 — Retrieve -> Reason -> Tool -> Validate -> Respond
        result = run_default_pipeline(
            trace=trace, understanding=understanding, provider=provider, request=request,
            conversation=conversation, user_msg=user_msg, user_text=user_text, facts_request=facts_request, verified_data=verified_data,
            respond=esc_respond, on_error=esc_on_error,
        )
        return investigate(esc_box.get("why", "escalation")) if result is ESCALATE else result
