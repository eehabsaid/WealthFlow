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
from core.services.certificate.certificate_balance_deduction_service import (
    CertificateBalanceMappingError,
    CertificateInsufficientBalanceError,
)

User = get_user_model()

import logging
import sys
import threading
import time
from django.conf import settings
from django.db.utils import OperationalError

_sync_lock = threading.Lock()
_last_sync_time = 0.0
_SYNC_DEBOUNCE_SECONDS = 5.0
logger = logging.getLogger(__name__)

def _is_testing():
    return getattr(settings, "TESTING", False) or ("test" in sys.argv)

def _run_certificate_interest_sync(force=False):
    global _last_sync_time
    now = time.time()
    testing = _is_testing()
    if not force and not testing and (now - _last_sync_time < _SYNC_DEBOUNCE_SECONDS):
        return None

    if not _sync_lock.acquire(blocking=False):
        return None

    try:
        now = time.time()
        if not force and not testing and (now - _last_sync_time < _SYNC_DEBOUNCE_SECONDS):
            return None

        from core.services.certificate.certificate_interest_service import CertificateInterestService
        result = CertificateInterestService().synchronize()
        _last_sync_time = time.time()
        return result
    except OperationalError as e:
        logger.warning(f"Certificate interest sync skipped due to DB lock: {e}")
        return None
    except Exception as e:
        logger.exception(f"Certificate interest sync error: {e}")
        return None
    finally:
        _sync_lock.release()

def _certificate_balance_error_response(exc):
    return JsonResponse(
        {"error_code": exc.error_code, "error": "; ".join(exc.messages)},
        status=400,
    )


@method_decorator(csrf_exempt, name="dispatch")
class BankCertificateListView(View):
    def get(self, request):
        certificates = BankCertificate.objects.select_related("bank", "currency").all()
        return JsonResponse({"certificates": [c.to_dict() for c in certificates]})

    def post(self, request):
        data = json.loads(request.body)
        try:
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
        except (CertificateBalanceMappingError, CertificateInsufficientBalanceError) as exc:
            return _certificate_balance_error_response(exc)
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
        try:
            certificate.save()
        except (CertificateBalanceMappingError, CertificateInsufficientBalanceError) as exc:
            return _certificate_balance_error_response(exc)
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

