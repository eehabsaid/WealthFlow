# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false
"""Users and roles, billing (plans, prices, gateway, customers) and Documentation tabs.

Part of the umbrella in core/views/settings/__init__.py (split so no file passes ~200 lines)."""

from core.views.settings.user.user_views import (
    UserListView,
    UserDetailView,
    UserBulkActionView,
    user_management_page,
)
from core.views.settings.user.user_permission_views import (
    UserPermissionListView,
    UserPermissionDetailView,
    PagePermissionChoicesView,
    UserRoleListView,
    UserRoleDetailView,
)
from core.views.settings.roles import (
    RoleListView,
    RoleDetailView,
)
from core.views.settings.billing.plan_admin_views import (
    PlanAdminListView,
    PlanAdminDetailView,
)
from core.views.settings.billing.plan_price_admin_views import (
    PlanPriceAdminListView,
    PlanPriceAdminDetailView,
)
from core.views.settings.billing.gateway_settings_views import PaymobGatewaySettingsView
from core.views.settings.billing.customer_admin_views import (
    CustomerActionView,
    CustomerListView,
    InvoiceActionView,
    TrialOptionsView,
    CustomerInvoicesView,
)
from core.views.settings.documentation.documentation_core_views import (
    ValidateCaptureView,
    ValidateGenerationView,
    DocumentationDevicesView,
    DocumentationStatusView,
    DocumentationHistoryView,
    GenerateDocumentationView,
)
from core.views.settings.documentation.documentation_action_views import (
    CaptureScreenshotsView,
    GenerateDocumentsView,
    CancelDocumentationView,
    OpenFolderView,
)

__all__ = [
    "UserListView",
    "UserDetailView",
    "UserBulkActionView",
    "user_management_page",
    "UserPermissionListView",
    "UserPermissionDetailView",
    "PagePermissionChoicesView",
    "UserRoleListView",
    "UserRoleDetailView",
    "RoleListView",
    "RoleDetailView",
    "PlanAdminListView",
    "PlanAdminDetailView",
    "PlanPriceAdminListView",
    "PlanPriceAdminDetailView",
    "PaymobGatewaySettingsView",
    "CustomerActionView",
    "CustomerListView",
    "InvoiceActionView",
    "TrialOptionsView",
    "ValidateCaptureView",
    "ValidateGenerationView",
    "DocumentationDevicesView",
    "DocumentationStatusView",
    "DocumentationHistoryView",
    "GenerateDocumentationView",
    "CaptureScreenshotsView",
    "GenerateDocumentsView",
    "CancelDocumentationView",
    "OpenFolderView",
    "CustomerInvoicesView",
]
