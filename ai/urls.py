"""All AI routes. Host projects add one line: path("", include("ai.urls"))."""

from .urls_chat import urlpatterns as chat
from .urls_platform import urlpatterns as platform
from .packs import url_patterns as pack_urls
from .urls_settings import urlpatterns as settings

urlpatterns = chat + platform + settings + pack_urls()
