# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from core.models import (
    BankCertificate,
    BankCertificateInterestHistory,

)

User = get_user_model()

def _run_certificate_interest_sync():
    from core.services.certificate.certificate_interest_service import CertificateInterestService

    return CertificateInterestService().synchronize()

@method_decorator(csrf_exempt, name="dispatch")
class BankCertificateListView(View):
    def get(self, request):
        certificates = BankCertificate.objects.select_related("bank", "currency").all()
        return JsonResponse({"certificates": [c.to_dict() for c in certificates]})

    def post(self, request):
        data = json.loads(request.body)
        certificate = BankCertificate.objects.create(
            bank_id=data["bank_id"],
            currency_id=data.get("currency_id"),
            issue_date=data.get("issue_date") or None,
            expiry_date=data.get("expiry_date") or None,
            amount=data.get("amount", 0),
            interest_rate=data.get("interest_rate", 0),
            interest_value=data.get("interest_value", 0),
            frequency=data.get("frequency", ""),
            status=data.get("status", "Active"),
            notes=data.get("notes", ""),
        )
        return JsonResponse(certificate.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class BankCertificateDetailView(View):
    def get(self, request, pk):
        certificate = get_object_or_404(BankCertificate, pk=pk)
        return JsonResponse(certificate.to_dict())

    def put(self, request, pk):
        certificate = get_object_or_404(BankCertificate, pk=pk)
        data = json.loads(request.body)
        for field in [
            "bank_id",
            "currency_id",
            "issue_date",
            "expiry_date",
            "amount",
            "interest_rate",
            "interest_value",
            "frequency",
            "status",
            "notes",
        ]:
            if field in data:
                setattr(certificate, field, data[field])
        certificate.save()
        return JsonResponse(certificate.to_dict())

    def delete(self, request, pk):
        certificate = get_object_or_404(BankCertificate, pk=pk)
        certificate.delete()
        return JsonResponse({"deleted": pk})

@method_decorator(csrf_exempt, name="dispatch")
class BankCertificateInterestHistoryView(View):
    def get(self, request, certificate_id):
        certificate = get_object_or_404(BankCertificate, pk=certificate_id)
        rows = (
            BankCertificateInterestHistory.objects.select_related("bank", "currency")
            .filter(certificate_id=certificate_id)
            .order_by("-posting_date", "-id")
        )

        start = request.GET.get("start")
        end = request.GET.get("end")
        if start:
            rows = rows.filter(posting_date__gte=start)
        if end:
            rows = rows.filter(posting_date__lte=end)

        return JsonResponse(
            {
                "certificate": certificate.to_dict(),
                "items": [row.to_dict() for row in rows],
            }
        )

