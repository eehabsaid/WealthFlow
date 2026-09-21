# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""NOTE: part of the settings/ai/ domain package. If this file
grows past ~200 lines, split it further within this folder and update
core/views/settings/__init__.py accordingly."""

from django.http import JsonResponse
from django.views import View

from core.views.auth_views import PermissionRequiredMixin
from core.integrations.ai_provider import AVAILABLE_AI_PROVIDERS


class AIProviderListView(PermissionRequiredMixin, View):
    required_key = "settings_aiadvisor"
    def get(self, request):
        providers = [
            cls.get_config_schema() for cls in AVAILABLE_AI_PROVIDERS.values()
        ]
        return JsonResponse({"providers": providers})
