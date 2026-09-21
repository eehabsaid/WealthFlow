# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""NOTE: single-resource file. If it grows past ~200 lines, split it and
move the resulting files into a settings/<domain>/ subfolder (see
settings/ai/ or settings/gold/ for the pattern: an empty __init__.py plus
one file per concern), then update core/views/settings/__init__.py."""


from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404

from core.validators.json_body import parse_json_body
from core.views.auth_views import PermissionRequiredMixin
from core.models import AppSettings, EmailTemplate
from core.services.shared.auth_workflow_service import AuthWorkflowService, EmailTemplateService


class EmailTemplateListView(PermissionRequiredMixin, View):
    required_key = "settings_emailtemplates"
    def get(self, request):
        lang = request.GET.get("lang", "en")
        return JsonResponse({"items": EmailTemplateService.list_templates(lang)})


class EmailTemplateDetailView(PermissionRequiredMixin, View):
    required_key = "settings_emailtemplates"
    def get(self, request, pk):
        lang = request.GET.get("lang", "en")
        template = get_object_or_404(EmailTemplate, pk=pk)
        EmailTemplateService.ensure_defaults()
        return JsonResponse(template.to_dict(lang))

    def put(self, request, pk):
        template = get_object_or_404(EmailTemplate, pk=pk)
        data = parse_json_body(request)
        lang = str(data.get("lang", "en") or "en")
        updated = EmailTemplateService.update_template(
            template,
            lang=lang,
            subject=(data.get("subject") or "").strip(),
            body=(data.get("body") or "").strip(),
        )
        return JsonResponse(updated.to_dict(lang))


class EmailSettingsTestView(PermissionRequiredMixin, View):
    required_key = "settings_emailtemplates"
    def post(self, request):
        data = parse_json_body(request)
        recipient = (data.get("to_email") or "").strip()
        if not recipient:
            recipient = (
                AppSettings.get("administrator_notification_email", "").strip()
                or AppSettings.get("sender_email", "").strip()
            )

        ok, message_key = AuthWorkflowService.send_smtp_test_email(to_email=recipient)
        return JsonResponse(
            {
                "ok": ok,
                "message_key": message_key,
            },
            status=200 if ok else 400,
        )
