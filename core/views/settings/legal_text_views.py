"""Legal Text settings tab (Privacy Policy / Terms of Service editor) and the
consent endpoints. Editing is sysadmin-only (SYSADMIN_ONLY_SETTINGS_TABS); the
consent status/accept endpoints are for any logged-in user."""

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from core.authentication.views.mixins import SysadminRequiredMixin
from core.models import LegalVersion, UserProfile
from core.services.legal import (
    LegalPublishError,
    accept_current,
    current_label,
    get_editor_payload,
    needs_reconsent,
    publish_version,
)
from core.validators.json_body import parse_json_body

ERROR_STATUS = {"duplicate_label": 409}


class LegalTextListView(SysadminRequiredMixin, View):
    def get(self, request):
        payload = get_editor_payload()
        payload["versions"] = [v.to_dict() for v in LegalVersion.objects.select_related("created_by")]
        return JsonResponse(payload)

    def post(self, request):
        data = parse_json_body(request)
        try:
            row = publish_version(
                label=data.get("label"),
                content=data.get("content"),
                require_reconsent=bool(data.get("require_reconsent")),
                user=request.user,
            )
        except LegalPublishError as exc:
            return JsonResponse({"error": exc.code}, status=ERROR_STATUS.get(exc.code, 400))
        return JsonResponse({"version": row.to_dict()}, status=201)


class LegalTextDetailView(SysadminRequiredMixin, View):
    def get(self, request, pk):
        row = get_object_or_404(LegalVersion, pk=pk)
        return JsonResponse({"version": row.to_dict(include_content=True)})


class LegalConsentView(View):
    """GET: does this account have to accept a newer version? POST: accept it."""

    @staticmethod
    def _profile(request):
        return UserProfile.objects.filter(user=request.user).first()

    def get(self, request):
        profile = self._profile(request)
        return JsonResponse(
            {
                "required": needs_reconsent(profile),
                "version": current_label(),
                "accepted_version": (profile.terms_version if profile else ""),
            }
        )

    def post(self, request):
        profile = self._profile(request)
        if profile is None:
            return JsonResponse({"error": "profile_missing"}, status=404)
        return JsonResponse({"accepted_version": accept_current(profile)})
