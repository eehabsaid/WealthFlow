from django.urls import path

from core.views import account_views

urlpatterns = [
    path("api/account/export/", account_views.account_export),
    path("api/account/delete/", account_views.account_delete),
]
