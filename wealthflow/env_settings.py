"""Environment-driven security settings (DEBUG, SECRET_KEY, hosts, HTTPS).

Pure function of an environ mapping so it can be unit-tested. Defaults keep
local development unchanged (DEBUG on, dev key, plain HTTP); setting
WEALTHFLOW_DEBUG=false switches everything to production-safe values.

Env vars (all optional except SECRET_KEY when DEBUG is off):
  WEALTHFLOW_DEBUG               true/false (default true)
  WEALTHFLOW_SECRET_KEY          required when DEBUG is false
  WEALTHFLOW_ALLOWED_HOSTS       comma list (default: the current hosts)
  WEALTHFLOW_CSRF_TRUSTED_ORIGINS comma list of https://... origins
  WEALTHFLOW_BEHIND_PROXY        true when a reverse proxy terminates TLS
  WEALTHFLOW_PROXY_COUNT         proxies in front of the app (default 1)
  WEALTHFLOW_SSL_REDIRECT        default true when DEBUG is false
  WEALTHFLOW_HSTS_SECONDS        default 2592000 (30 days) when DEBUG is false
"""
from django.core.exceptions import ImproperlyConfigured

DEV_SECRET_KEY = "django-insecure-8pg_zmp_cy^rl+p7=hb3ournneiqklid=m4z1x-69j6-u+#77g"
DEFAULT_HOSTS = ["wealthflow.pythonanywhere.com", "localhost", "127.0.0.1"]
DEFAULT_TRUSTED_ORIGINS = ["https://wealthflow.pythonanywhere.com"]


def _bool(environ, name, default):
    raw = environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _list(environ, name, default):
    raw = environ.get(name)
    if raw is None or not str(raw).strip():
        return list(default)
    return [item.strip() for item in str(raw).split(",") if item.strip()]


def _int(environ, name, default):
    try:
        return int(str(environ.get(name, "")).strip())
    except ValueError:
        return default


def build_security_settings(environ) -> dict:
    debug = _bool(environ, "WEALTHFLOW_DEBUG", True)
    secret = (environ.get("WEALTHFLOW_SECRET_KEY") or "").strip()
    if not secret:
        if not debug:
            raise ImproperlyConfigured("WEALTHFLOW_SECRET_KEY must be set when WEALTHFLOW_DEBUG is false.")
        secret = DEV_SECRET_KEY

    cfg = {
        "DEBUG": debug,
        "SECRET_KEY": secret,
        "ALLOWED_HOSTS": _list(environ, "WEALTHFLOW_ALLOWED_HOSTS", DEFAULT_HOSTS),
        "CSRF_TRUSTED_ORIGINS": _list(environ, "WEALTHFLOW_CSRF_TRUSTED_ORIGINS", DEFAULT_TRUSTED_ORIGINS),
    }
    if not debug:
        cfg.update(
            SESSION_COOKIE_SECURE=True,
            CSRF_COOKIE_SECURE=True,
            SECURE_SSL_REDIRECT=_bool(environ, "WEALTHFLOW_SSL_REDIRECT", True),
            SECURE_HSTS_SECONDS=_int(environ, "WEALTHFLOW_HSTS_SECONDS", 2592000),
            SECURE_CONTENT_TYPE_NOSNIFF=True,
        )
    if _bool(environ, "WEALTHFLOW_BEHIND_PROXY", False):
        cfg["SECURE_PROXY_SSL_HEADER"] = ("HTTP_X_FORWARDED_PROTO", "https")
        cfg["USE_X_FORWARDED_HOST"] = True
        # django-axes: read the real client IP from X-Forwarded-For.
        cfg["AXES_IPWARE_PROXY_COUNT"] = _int(environ, "WEALTHFLOW_PROXY_COUNT", 1)
        cfg["AXES_IPWARE_META_PRECEDENCE_ORDER"] = ("HTTP_X_FORWARDED_FOR", "REMOTE_ADDR")
    return cfg
