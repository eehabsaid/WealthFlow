# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false

"""NOTE: part of the settings/user/ domain package. If this file grows
past ~200 lines, split it further within this folder and update
core/views/settings/__init__.py accordingly.

`page` here means any key in the unified permission-key namespace (main-app
pages + settings tabs) — see core/constants/roles.py. A PagePermission row
is a per-user override: `granted=True` grants the key even without a role;
`granted=False` revokes it even if a role grants it. Overrides always win."""

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404

from core.validators.json_body import parse_json_body
from core.models import PagePermission
from core.constants.roles import grantable_permission_choices, grantable_permission_keys
from core.views.auth_views import AdminRequiredMixin

User = get_user_model()


class UserPermissionListView(AdminRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        permissions = user.page_permissions.all()
        return JsonResponse(
            {
                "permissions": [perm.to_dict() for perm in permissions],
                "available_pages": grantable_permission_choices(),
            }
        )

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        data = parse_json_body(request)
        page = data.get("page")
        granted = bool(data.get("granted", True))
        if page not in grantable_permission_keys():
            return JsonResponse({"error": "Invalid permission key"}, status=400)
        perm, created = PagePermission.objects.update_or_create(
            user=user, page=page, defaults={"granted": granted}
        )
        return JsonResponse(
            {"permission": perm.to_dict()}, status=201 if created else 200
        )


class UserPermissionDetailView(AdminRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, pk):
        perm = get_object_or_404(PagePermission, pk=pk)
        perm.delete()
        return JsonResponse({"deleted": pk})


class PagePermissionChoicesView(AdminRequiredMixin, View):
    def get(self, request):
        return JsonResponse({"available_pages": grantable_permission_choices()})


class UserRoleListView(AdminRequiredMixin, View):
    """Roles currently assigned to a user (a user may hold several); POST
    assigns one more."""

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        return JsonResponse({"roles": [ur.to_dict() for ur in user.roles.all()]})

    def post(self, request, pk):
        from core.models.permissions import Role, UserRole

        user = get_object_or_404(User, pk=pk)
        data = parse_json_body(request)
        role = get_object_or_404(Role, pk=data.get("role_id"))
        ur, created = UserRole.objects.get_or_create(user=user, role=role)
        return JsonResponse({"user_role": ur.to_dict()}, status=201 if created else 200)


class UserRoleDetailView(AdminRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, pk):
        from core.models.permissions import UserRole

        ur = get_object_or_404(UserRole, pk=pk)
        ur.delete()
        return JsonResponse({"deleted": pk})
