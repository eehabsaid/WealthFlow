"""AI actions with confirmation: the model PROPOSES an add / edit / delete; nothing changes until the user presses
Confirm on the card. Writes reuse the app's own services, always scoped to the signed-in user."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from ai.models.ai_chat_block import AIChatBlock

from ai.services.actions import codefile, expense, income, reminder
from ai.services.actions.cards import make_card
from ai.services.actions.common import ActionError

HANDLERS = {"expense": expense, "reminder": reminder, "income": income, "code_file": codefile}
MODEL_RECORDS = ("expense", "reminder", "income")   # what propose_action may touch; code_file only through app_propose_edit
OPS = ("add", "edit", "delete")


def propose_action(user, params: dict) -> dict:
    """Tool handler: build a pending card. Never writes business data."""
    record, op = str(params.get("record") or ""), str(params.get("op") or "")
    if record not in MODEL_RECORDS or op not in OPS:
        return {"error": f"`record` must be one of {list(MODEL_RECORDS)} and `op` one of {list(OPS)}"}
    target = params.get("target") if isinstance(params.get("target"), dict) else {}
    values = params.get("values") if isinstance(params.get("values"), dict) else {}
    try:
        payload = HANDLERS[record].propose(user, op, target, values)
    except ActionError as exc:
        return {"error": str(exc)}
    return make_card(user, payload)


def decide(user, block_id: int, confirm: bool, edits: dict | None = None) -> tuple[dict, int]:
    """Confirm or cancel one pending card of this user (with the values the user changed on the card). Returns (json, http status)."""
    with transaction.atomic():
        block = AIChatBlock.objects.select_for_update().filter(pk=block_id, user=user, kind=AIChatBlock.KIND_ACTION).first()
        if block is None:
            return {"error": "not_found"}, 404
        if block.status != AIChatBlock.STATUS_PENDING:
            return {"error": "already_decided", "block": block.to_dict()}, 409
        if confirm and edits and block.payload.get("editable") and hasattr(HANDLERS[block.payload["record"]], "apply_edits"):
            try:   # a wrong value typed on the card is sent back to the user; the card stays pending so it can be corrected
                params = HANDLERS[block.payload["record"]].apply_edits(user, block.payload, edits)
                rows = [{**r, ("after" if "after" in r else "value"): str(edits.get(r["label"], r.get("after", r.get("value"))))} for r in block.payload["rows"]]
                block.payload = {**block.payload, "params": params, "rows": rows}   # the finished card shows what was really saved
            except ActionError as exc:
                return {"error": str(exc), "block": block.to_dict()}, 422
        block.decided_at = timezone.now()
        if not confirm:
            block.status, block.result = AIChatBlock.STATUS_CANCELLED, ""
        else:
            p = block.payload
            try:
                with transaction.atomic():
                    block.result = HANDLERS[p["record"]].execute(user, p["op"], p["params"])
                block.status = AIChatBlock.STATUS_CONFIRMED
            except ActionError as exc:
                block.status, block.result = AIChatBlock.STATUS_FAILED, str(exc)
        block.save()
    if block.status == AIChatBlock.STATUS_CONFIRMED:
        try:
            from core.authentication.utils.auth_utils import record_audit
            record_audit(user, "ai_action_confirmed", actor=user, details=f"{block.payload.get('op')} {block.payload.get('record')} {block.result}"[:250])
        except Exception:
            pass  # the audit trail must never undo a saved change
    return {"block": block.to_dict()}, 200


def cancel_cards_of(user, message_ids) -> int:
    """Edit-and-resend hides old messages: their cards that were never confirmed are cancelled so they cannot be confirmed later."""
    return AIChatBlock.objects.filter(user=user, kind=AIChatBlock.KIND_ACTION, status=AIChatBlock.STATUS_PENDING, message_id__in=list(message_ids)).update(
        status=AIChatBlock.STATUS_CANCELLED, decided_at=timezone.now())


def attach_blocks(user, since, message) -> None:
    """After an answer is saved: the cards / charts created while writing it belong to that answer."""
    AIChatBlock.objects.filter(user=user, message__isnull=True, created_at__gte=since).update(message=message)
