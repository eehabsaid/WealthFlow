from django.urls import path
from . import views

urlpatterns = [
    path("translations/", views.get_translations),
    path("translations/save/", views.save_translations),
    path("translations/scan/", views.scan_translations),
    path('api/scan-translations/', views.scan_translations, name='scan_translations'),
]