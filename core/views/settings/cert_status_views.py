# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""NOTE: single-resource file. If it grows past ~200 lines, split it and
move the resulting files into a settings/<domain>/ subfolder (see
settings/ai/ or settings/gold/ for the pattern: an empty __init__.py plus
one file per concern), then update core/views/settings/__init__.py."""

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from core.models import CertificateStatus


@method_decorator(csrf_exempt, name="dispatch")
class CertificateStatusListView(View):
    def get(self, request):
        statuses = CertificateStatus.objects.all()
        return JsonResponse({"statuses": [s.to_dict() for s in statuses]})

    def post(self, request):
        data = json.loads(request.body)
        # If new status is default, unset any existing default
        if data.get("is_default"):
            CertificateStatus.objects.filter(is_default=True).update(is_default=False)
        s = CertificateStatus.objects.create(
            name=data["name"],
            color_hex=data.get("color_hex", "#1a6ef5"),
            is_default=data.get("is_default", False),
            is_terminal=data.get("is_terminal", False),
            order=int(data.get("order", 0)),
        )
        return JsonResponse({"status": s.to_dict()}, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class CertificateStatusDetailView(View):
    def put(self, request, pk):
        s = get_object_or_404(CertificateStatus, pk=pk)
        data = json.loads(request.body)
        if data.get("is_default") and not s.is_default:
            CertificateStatus.objects.filter(is_default=True).update(is_default=False)
        s.name = data.get("name", s.name)
        s.color_hex = data.get("color_hex", s.color_hex)
        s.is_default = data.get("is_default", s.is_default)
        s.is_terminal = data.get("is_terminal", s.is_terminal)
        s.order = int(data.get("order", s.order))
        s.save()
        return JsonResponse({"status": s.to_dict()})

    def delete(self, request, pk):
        s = get_object_or_404(CertificateStatus, pk=pk)
        s.delete()
        return JsonResponse({"deleted": pk})
