"""Ask mode -> Agent mode for a request Ask cannot do well: a written document ABOUT the application (a user guide as Word / PDF / HTML).
Ask answers from a small slice of the data and invents the rest; Agent mode reads the live screens. The request is moved to Agent mode
(the chat's mode bar follows, see the "chat_mode" key of the response) when: Agent mode is switched on by the administrator, a document
file is requested, the domain allows a guide (the App domain keeps its own refusal), and the model answers YES to the fixed
English question of core.services.ai.protocol.ABOUT_APP_PROMPT (no word lists)."""

from __future__ import annotations

import time

from core.services.ai.domains import APP

from .settings import agent_enabled, set_chat_mode

QUESTION_BUDGET_S = 30


class _Calls:   # what compose._ask counts on the object it is given
    llm_calls = 0
    cut_off = False
    cancel_check = None
    cancelled = False


def moves_to_agent(user, user_text: str, provider, domain: str = "") -> bool:
    """True (and the user's saved mode becomes "agent") when this Ask-mode request must run in Agent mode."""
    from core.views.ai_chat.chat_pipeline.document_request import wants_written_document

    if domain == APP or not agent_enabled() or not wants_written_document(user_text):
        return False
    from core.services.ai.investigation.compose import _about_the_app

    if not _about_the_app(provider, user_text, _Calls(), time.monotonic() + QUESTION_BUDGET_S):
        return False
    set_chat_mode(user, "agent")
    return True
