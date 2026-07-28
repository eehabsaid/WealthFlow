# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false
import json
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q

from core.models import (
    PagePermission,
    PAGE_PERMISSION_CHOICES,
)
from core.constants import (
    PAGE_PERMISSION_KEYS,
)
from core.services.shared.auth_workflow_service import AuthWorkflowService
from core.views.auth_views import AdminRequiredMixin, _build_user_dict

User = get_user_model()

class UserListView(AdminRequiredMixin, View):
    def get(self, request):
        q = request.GET.get("q", "").strip()
        page = int(request.GET.get("page", 1) or 1)
        page_size = int(request.GET.get("page_size", 20) or 20)

        qs = User.objects.order_by("username").all()
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q))

        paginator = Paginator(qs, page_size)
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        users = [_build_user_dict(u) for u in page_obj.object_list]
        return JsonResponse(
            {
                "users": users,
                "page": page_obj.number,
                "page_size": page_size,
                "total": paginator.count,
                "num_pages": paginator.num_pages,
            }
        )

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        data = json.loads(
            request.body.decode("utf-8")
            if isinstance(request.body, bytes)
            else request.body
        )
        username = data.get("username", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password", "")
        if not username or not email or not password:
            return JsonResponse(
                {"error": "username, email and password are required"}, status=400
            )
        if User.objects.filter(username=username).exists():
            return JsonResponse({"error": "Username is already taken"}, status=400)
        user = User.objects.create_user(
            username=username, email=email, password=password
        )
        user.is_active = data.get("is_active", True)
        user.is_staff = data.get("is_staff", False)
        user.is_superuser = data.get("is_superuser", False)
        user.save()
        if user.is_active:
            AuthWorkflowService.enable_user(user, actor=request.user)
        else:
            AuthWorkflowService.disable_user(user, actor=request.user)
        return JsonResponse({"user": _build_user_dict(user)}, status=201)

class UserDetailView(AdminRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        return JsonResponse({"user": _build_user_dict(user)})

    def put(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        original_is_active = user.is_active
        data = json.loads(
            request.body.decode("utf-8")
            if isinstance(request.body, bytes)
            else request.body
        )
        for field in ["email", "is_active", "is_staff", "is_superuser"]:
            if field in data:
                setattr(user, field, data[field])
        if data.get("password"):
            user.set_password(data["password"])
        user.save()
        if "is_active" in data and data["is_active"] != original_is_active:
            if data["is_active"]:
                AuthWorkflowService.enable_user(user, actor=request.user)
            else:
                AuthWorkflowService.disable_user(user, actor=request.user)
        return JsonResponse({"user": _build_user_dict(user)})

    def delete(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.delete()
        return JsonResponse({"deleted": pk})

class UserPermissionListView(AdminRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        permissions = user.page_permissions.all()
        return JsonResponse(
            {
                "permissions": [perm.to_dict() for perm in permissions],
                "available_pages": PAGE_PERMISSION_CHOICES,
            }
        )

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        data = json.loads(
            request.body.decode("utf-8")
            if isinstance(request.body, bytes)
            else request.body
        )
        page = data.get("page")
        if page not in PAGE_PERMISSION_KEYS:
            return JsonResponse({"error": "Invalid page permission"}, status=400)
        perm, created = PagePermission.objects.get_or_create(user=user, page=page)
        return JsonResponse(
            {"permission": perm.to_dict()}, status=201 if created else 200
        )

class UserBulkActionView(AdminRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        data = json.loads(
            request.body.decode("utf-8")
            if isinstance(request.body, bytes)
            else request.body
        )
        action = data.get("action")
        ids = data.get("ids") or []
        if not action or not isinstance(ids, list):
            return JsonResponse({"error": "action and ids required"}, status=400)

        users = User.objects.filter(id__in=ids)
        changed = 0
        if action == "delete":
            changed = users.count()
            users.delete()
        elif action == "activate":
            changed = users.count()
            for user in users:
                AuthWorkflowService.enable_user(user, actor=request.user)
        elif action == "deactivate":
            changed = users.count()
            for user in users:
                AuthWorkflowService.disable_user(user, actor=request.user)
        elif action == "set_staff":
            val = bool(data.get("value"))
            changed = users.update(is_staff=val)
        elif action == "set_superuser":
            val = bool(data.get("value"))
            changed = users.update(is_superuser=val)
        else:
            return JsonResponse({"error": "unknown action"}, status=400)

        return JsonResponse({"changed": changed})

class UserPermissionDetailView(AdminRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, pk):
        perm = get_object_or_404(PagePermission, pk=pk)
        perm.delete()
        return JsonResponse({"deleted": pk})

class PagePermissionChoicesView(AdminRequiredMixin, View):
    def get(self, request):
        return JsonResponse({"available_pages": PAGE_PERMISSION_CHOICES})

@login_required(login_url="/accounts/login/")
def user_management_page(request):
    if not request.user.is_staff:
        return redirect("/")
    return render(request, "user_management.html")
