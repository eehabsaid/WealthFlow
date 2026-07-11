import os
import sys
import django
from django.urls import get_resolver

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wealthflow.settings")
django.setup()

def get_all_urls():
    urlconf = __import__(django.conf.settings.ROOT_URLCONF, {}, {}, [''])
    resolver = get_resolver(urlconf)
    
    # Just accessing the URL patterns will trigger importing all the views and loading them
    return list(resolver.url_patterns)

try:
    patterns = get_all_urls()
    print("Successfully loaded URL patterns without errors.")
except Exception as e:
    print(f"Error loading URLs: {e}")
    sys.exit(1)
