"""
Django settings for wealthflow project.
"""

import os
from datetime import timedelta

from dotenv import load_dotenv

from wealthflow.env_settings import build_security_settings

# Build paths inside the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from a local .env file if present (e.g.
# WF_USERNAME/WF_PASSWORD for the documentation/QA screenshot tooling).
# Safe no-op when no .env file exists. Never commit a real .env file -
# see .env.example for the expected keys.
load_dotenv(os.path.join(BASE_DIR, ".env"))

# DEBUG, SECRET_KEY, ALLOWED_HOSTS, CSRF origins and HTTPS hardening come from
# the environment (see wealthflow/env_settings.py). Defaults keep local
# development unchanged; WEALTHFLOW_DEBUG=false turns on production settings.
globals().update(build_security_settings(os.environ))

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "axes",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "axes.middleware.AxesMiddleware",
    "core.middleware.LoginRequiredMiddleware",
    "core.middleware.JsonBodyErrorMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "wealthflow.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "wealthflow.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        # Overridable so tooling (e.g. scripts/run_e2e_tests.sh) can point the
        # app at a disposable copy of the database instead of production.
        "NAME": os.path.join(BASE_DIR, os.environ.get("WEALTHFLOW_DB_NAME", "db.sqlite3")),
        "OPTIONS": {
            "timeout": 20,
        },
    }
}

# FIX 2: Add this to remove the W042 warnings
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/accounts/login/"

# ── Brute-force protection (django-axes) ────────────────────────────────────
# Lock a username+IP pair after 5 failed logins for 15 minutes. Behind a
# reverse proxy, set WEALTHFLOW_BEHIND_PROXY=true (and WEALTHFLOW_PROXY_COUNT)
# so the real client IP is used instead of the proxy's; see env_settings.py.
AUTHENTICATION_BACKENDS = [
    "core.authentication.backends.RequestOptionalAxesBackend",
    "django.contrib.auth.backends.ModelBackend",
]
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_CALLABLE = "core.authentication.lockout.lockout_response"
LOGIN_REDIRECT_URL = "/"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Cairo"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Media files (user uploads — profile pictures)
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Playwright Documentation Backend ('python' or 'javascript')
PLAYWRIGHT_BACKEND = os.environ.get("PLAYWRIGHT_BACKEND", "python").lower()
