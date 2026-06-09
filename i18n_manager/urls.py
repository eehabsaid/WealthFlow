from django.urls import path
from . import views

urlpatterns = [
    path("translations/", views.get_translations),
    path("translations/save/", views.save_translations),
]