"""Stage 1 of the chat request — Understand (deterministic, no LLM): which domain applies and what the user means."""

from core.services.ai.domains import APP, BUSINESS, app_enabled, resolve_domain
from core.views.ai_chat.chat_pipeline import understand


def understand_request(body, user_text, trace):
    """(domain, understanding). The sysadmin's allowed chat domains win over what the browser sent (Settings > AI Advisor > Chat domains)."""
    with trace.stage("understand") as rec:
        chosen = resolve_domain(str(body.get("question_domain", "")))   # "" = none chosen and both allowed: inferred
        # Strict rules (tools, context, knowledge paths): the App domain, and Business when the sysadmin switched the App domain off.
        # Business chosen while both are allowed keeps the usual paths (how-do-I-record-it answers use the app knowledge).
        domain = chosen if chosen == APP or (chosen == BUSINESS and not app_enabled()) else ""
        understanding = understand(user_text, chosen)
        understanding.enforced = domain
        rec.detail.update(understanding.to_dict())
    return domain, understanding
