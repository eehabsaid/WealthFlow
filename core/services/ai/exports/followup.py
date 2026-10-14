"""A bare "export it to Excel" / "and as a PDF?" exports the previous answer instead of asking the model.

It is a follow-up only when a file is wanted AND there is an earlier answer to export AND the message names no data
topic AND the query engine finds no capability in it AND little else is left once the file request is removed
("export it to pdf" leaves two words; "analyze my wealth ... in details and export to word" leaves a whole question).
"export the loans to excel" or "export my salaries 2026" are data questions and go through the normal pipeline
(their own answer then gets the links), and so is any other real question, even one the router cannot compute."""

from __future__ import annotations

import re
from typing import Any

from .document import strip_export_lines

FOLLOWUP_TOOL = "export_followup"
FOLLOWUP_MAX_WORDS = 5   # words left after the file request is stripped; more than this is a question of its own


# Words that may remain once the file request is removed and it is still only "export it": "export the previous answer
# to Excel please" -> "the previous answer to please". Anything else ("write a haiku and save it as .txt", "write a python
# function ...") is a NEW request that happens to name a file type, never a follow-up, however short it is.
_FILLER = frozenset(
    "it this that them these those the a an to in as and also then too please again now same previous last latest answer answers result results "
    "reply response above file files sheet document doc one me my for of from on is are can could you pls plz "
    "هذا هذه ذلك تلك الاجابه الاجابة الإجابة السابق السابقه السابقة النتيجه النتيجة النتائج و في الى إلى ك ل لو سمحت من فضلك مره اخرى ملف "
    "le la les l ça ca cela ce cette en au aux sous et aussi svp merci précédent precedent précédente réponse reponse résultat resultat fichier un une des de du "
    "s'il vous te tu plaît plait es das die den dem als nach und auch bitte vorherige vorherigen antwort ergebnis datei eine einen ein".split()
)
_TOKEN = re.compile(r"[\w']+", re.UNICODE)


def only_a_file_request(remainder: str) -> bool:
    """True when nothing but filler words is left of the message after its export terms were stripped."""
    return all(tok in _FILLER for tok in _TOKEN.findall(str(remainder or "").lower()))


def is_pure_followup(routing: Any, understanding: Any, remaining_text: str = "") -> bool:
    """`routing`: query_engine Routing for the message; `understanding`: chat_pipeline Understanding;
    `remaining_text`: the message without its file request (strip_export_terms). Short (FOLLOWUP_MAX_WORDS) AND only
    filler words left AND nothing the router or the topic detector can look up."""
    if len(str(remaining_text or "").split()) > FOLLOWUP_MAX_WORDS or not only_a_file_request(remaining_text):
        return False
    return getattr(routing, "status", "") == "none" and not list(getattr(understanding, "topics", None) or [])


def previous_answer(conversation: Any, before_message_id: int) -> Any | None:
    """Latest earlier assistant answer that is real content (not an export-follow-up note)."""
    for msg in conversation.messages.filter(role="assistant", is_deleted=False, id__lt=before_message_id).order_by("-id"):
        calls = msg.tool_calls or []
        if any(isinstance(c, dict) and c.get("tool") == FOLLOWUP_TOOL for c in calls):
            continue
        if strip_export_lines(msg.content).strip():
            return msg
    return None
