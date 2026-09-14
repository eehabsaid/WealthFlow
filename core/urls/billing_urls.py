from django.urls import path

from core.views import billing_views

urlpatterns = [
    path("api/billing/status/", billing_views.billing_status),
    path("api/billing/plans/", billing_views.billing_plans),
]
