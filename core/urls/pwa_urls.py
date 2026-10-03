from django.urls import path
from .. import views

urlpatterns = [
    path("manifest.webmanifest", views.manifest_view, name="pwa-manifest"),
    path("service-worker.js", views.service_worker_view, name="pwa-service-worker"),
    path("offline/", views.offline_view, name="pwa-offline"),
]
