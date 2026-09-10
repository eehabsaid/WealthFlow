# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from core.models import ExpenseCategory, ExpenseSubcategory
from core.validators import _api_auth_required, _owned_queryset, _owned_object_or_404, _child_owned_object_or_404


@method_decorator(csrf_exempt, name="dispatch")
class ExpenseCategoryListView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        cats = _owned_queryset(ExpenseCategory, request).prefetch_related("subcategories")
        data = []
        for c in cats:
            d = c.to_dict()
            d["subcategories"] = [s.to_dict() for s in c.subcategories.all()]
            data.append(d)
        return JsonResponse({"categories": data})

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        data = json.loads(request.body)
        cat = ExpenseCategory.objects.create(
            owner=request.user,
            name=data["name"],
            icon=data.get("icon", "💰"),
            color_hex=data.get("color_hex", "#0d6efd"),
            order=data.get("order", 0),
        )
        return JsonResponse(cat.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class ExpenseCategoryDetailView(View):
    def put(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        cat = _owned_object_or_404(ExpenseCategory, pk, request)
        data = json.loads(request.body)
        for f in ["name", "icon", "color_hex", "order"]:
            if f in data:
                setattr(cat, f, data[f])
        cat.save()
        return JsonResponse(cat.to_dict())

    def delete(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        cat = _owned_object_or_404(ExpenseCategory, pk, request)
        cat.delete()
        return JsonResponse({"deleted": pk})

@method_decorator(csrf_exempt, name="dispatch")
class ExpenseSubcategoryListView(View):
    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        data = json.loads(request.body)
        category = _owned_object_or_404(ExpenseCategory, data["category_id"], request)
        sub = ExpenseSubcategory.objects.create(
            category=category,
            name=data["name"],
            order=data.get("order", 0),
        )
        return JsonResponse(sub.to_dict(), status=201)

@method_decorator(csrf_exempt, name="dispatch")
class ExpenseSubcategoryDetailView(View):
    def put(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        sub = _child_owned_object_or_404(ExpenseSubcategory, pk, request, parent_field="category")
        data = json.loads(request.body)
        for f in ["name", "order"]:
            if f in data:
                setattr(sub, f, data[f])
        sub.save()
        return JsonResponse(sub.to_dict())

    def delete(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        sub = _child_owned_object_or_404(ExpenseSubcategory, pk, request, parent_field="category")
        sub.delete()
        return JsonResponse({"deleted": pk})
