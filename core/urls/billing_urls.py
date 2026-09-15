from django.urls import path

from core.views import billing_views

urlpatterns = [
    path("api/billing/status/", billing_views.billing_status),
    path("api/billing/plans/", billing_views.billing_plans),
    path("api/billing/upgrade-request/", billing_views.billing_upgrade_request),
    path("api/billing/checkout/", billing_views.billing_checkout),
    path("api/billing/checkout/fake-complete/", billing_views.billing_checkout_fake_complete),
    path("api/billing/paymob/webhook/", billing_views.paymob_webhook),
]
