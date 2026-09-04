# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""NOTE: single-resource file. If it grows past ~200 lines, split it and
move the resulting files into a settings/<domain>/ subfolder (see
settings/ai/ or settings/gold/ for the pattern: an empty __init__.py plus
one file per concern), then update core/views/settings/__init__.py."""

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.views.auth_views import AdminRequiredMixin
from core.services.shared.vendor_assets_updater_service import update_vendor_assets

# ══════════════════════════════════════════════════════════════
# OFFLINE VENDOR ASSETS UPDATE VIEW
# ══════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class VendorAssetsUpdateView(AdminRequiredMixin, View):
    def post(self, request):
        updated, success, message = update_vendor_assets()
        return JsonResponse({"success": success, "updated": updated, "message": message})
