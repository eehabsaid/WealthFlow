# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""NOTE: part of the settings/ai/ domain package. If this file
grows past ~200 lines, split it further within this folder and update
core/views/settings/__init__.py accordingly."""

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.views.auth_views import AdminRequiredMixin
from core.integrations.ai_provider import AVAILABLE_AI_PROVIDERS


@method_decorator(csrf_exempt, name="dispatch")
class AIProviderListView(AdminRequiredMixin, View):
    def get(self, request):
        providers = [
            cls.get_config_schema() for cls in AVAILABLE_AI_PROVIDERS.values()
        ]
        return JsonResponse({"providers": providers})
