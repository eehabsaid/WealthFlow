# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""Role CRUD — sysadmin-only. Roles are the delegable half of the access
system: an admin-defined bundle of grantable keys (see
core/constants/roles.py) assigned to users via UserRole. Managing Roles
itself is intentionally NOT delegable (SYSADMIN_ONLY_SETTINGS_TABS)."""

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.db import IntegrityError

from core.models.permissions import Role, RolePermission
from core.constants.roles import grantable_permission_choices, grantable_permission_keys
from core.views.auth_views import AdminRequiredMixin


def _set_role_keys(role, keys):
    valid = set(grantable_permission_keys())
    keys = [k for k in (keys or []) if k in valid]
    RolePermission.objects.filter(role=role).exclude(key__in=keys).delete()
    existing = set(role.permissions.values_list("key", flat=True))
    RolePermission.objects.bulk_create(
        [RolePermission(role=role, key=k) for k in keys if k not in existing]
    )


class RoleListView(AdminRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        roles = Role.objects.all().prefetch_related("permissions")
        return JsonResponse(
            {
                "roles": [r.to_dict() for r in roles],
                "available_keys": grantable_permission_choices(),
            }
        )

    def post(self, request):
        data = json.loads(
            request.body.decode("utf-8")
            if isinstance(request.body, bytes)
            else request.body
        )
        name = (data.get("name") or "").strip()
        if not name:
            return JsonResponse({"error": "Role name is required"}, status=400)
        try:
            role = Role.objects.create(
                name=name, description=data.get("description", "")
            )
        except IntegrityError:
            return JsonResponse({"error": "A role with that name already exists"}, status=400)
        _set_role_keys(role, data.get("keys"))
        return JsonResponse({"role": role.to_dict()}, status=201)


class RoleDetailView(AdminRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def put(self, request, pk):
        role = get_object_or_404(Role, pk=pk)
        data = json.loads(
            request.body.decode("utf-8")
            if isinstance(request.body, bytes)
            else request.body
        )
        if "name" in data:
            name = (data.get("name") or "").strip()
            if not name:
                return JsonResponse({"error": "Role name is required"}, status=400)
            role.name = name
        if "description" in data:
            role.description = data.get("description", "")
        try:
            role.save()
        except IntegrityError:
            return JsonResponse({"error": "A role with that name already exists"}, status=400)
        if "keys" in data:
            _set_role_keys(role, data.get("keys"))
        return JsonResponse({"role": role.to_dict()})

    def delete(self, request, pk):
        role = get_object_or_404(Role, pk=pk)
        role.delete()
        return JsonResponse({"deleted": pk})
