"""Self-service account endpoints. Under /api/account/ so lapsed users can still export or delete (middleware exempt)."""

import json
import logging

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

from core.services.account import build_user_export, deletion_blocker, grace_days, schedule_deletion
from core.validators.json_body import parse_json_body

logger = logging.getLogger(__name__)

CONFIRM_WORD = "DELETE"


@login_required(login_url="/accounts/login/")
def account_export(request):
    """GET: download everything the signed-in user owns as JSON."""
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    payload = build_user_export(request.user)
    stamp = timezone.now().strftime("%Y%m%d-%H%M%S")
    response = HttpResponse(json.dumps(payload, ensure_ascii=False, indent=1), content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="wealthflow-my-data-{stamp}.json"'
    response["Cache-Control"] = "no-store"
    return response


@login_required(login_url="/accounts/login/")
def account_delete(request):
    """POST {confirm: "DELETE", password}: disable the account and schedule its deletion; restorable during the grace period."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    data = parse_json_body(request)
    user = request.user
    if str(data.get("confirm", "")).strip() != CONFIRM_WORD:
        return JsonResponse({"error": "confirmation_required"}, status=400)
    if user.has_usable_password() and not user.check_password(str(data.get("password", ""))):
        return JsonResponse({"error": "invalid_password"}, status=403)
    blocker = deletion_blocker(user)
    if blocker:
        return JsonResponse({"error": "last_admin", "message": blocker}, status=409)
    purge_on = schedule_deletion(user, actor=user)
    logout(request)
    return JsonResponse({"deleted": True, "scheduled": True, "grace_days": grace_days(), "purge_at": purge_on.isoformat() if purge_on else None})
