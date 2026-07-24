from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Add this line to handle the browser's automatic favicon lookup
    path("favicon.ico", RedirectView.as_view(url="/static/images/favicon.ico")),
    path("", include("core.urls")),
    path("api/", include("i18n_manager.urls")),
]

# This is the correct way to handle static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)