from django.urls import path
from .. import views

urlpatterns = [
    path("api/import/preview/", views.ImportPreviewView.as_view()),
    path("api/import/confirm/", views.ImportConfirmView.as_view()),
]
