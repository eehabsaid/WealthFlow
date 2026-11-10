"""Portability proof: copy ONLY ai/ into (1) a brand-new Django project and (2) an independent project with its own
apps, follow ai/INSTALL.md, migrate, hit the routes and run ai/tests.

  python scripts/ai_portability_check.py [--keep]
"""
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from collections import deque
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IGNORE = shutil.ignore_patterns("__pycache__", "node_modules", "*.pyc", "output", ".pytest_cache")
SETTINGS = '''
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "x"; DEBUG = True; ALLOWED_HOSTS = ["*"]
INSTALLED_APPS = ["django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
                  "django.contrib.messages", "django.contrib.staticfiles"%(apps)s, "ai"]
MIDDLEWARE = ["django.contrib.sessions.middleware.SessionMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware",
              "django.contrib.messages.middleware.MessageMiddleware"]
ROOT_URLCONF = "proj.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.contrib.auth.context_processors.auth"]}}]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"
USE_TZ = True
%(extra)s
'''
URLS = 'from django.urls import include, path\nurlpatterns = [path("", include("ai.urls"))%(extra)s]\n'
SMOKE = '''
import django; django.setup()
from django.contrib.auth import get_user_model
from django.test import Client
U = get_user_model()
u, _ = U.objects.get_or_create(username="admin", defaults={"is_superuser": True, "is_staff": True}); u.set_password("pw"); u.save()
c = Client(); assert c.login(username="admin", password="pw")
for url in ("/api/settings/ai/", "/api/financial-advisor/ai/conversations/"):
    r = c.get(url, HTTP_HOST="localhost"); print(url, r.status_code); assert r.status_code == 200, r.content[:300]
r = Client().get("/api/settings/ai/", HTTP_HOST="localhost"); print("anon", r.status_code); assert r.status_code in (401, 403, 302)
'''


def run(cmd, cwd, env_extra=None, stream=False):
    env = {**os.environ, "DJANGO_SETTINGS_MODULE": "proj.settings", **(env_extra or {})}
    if stream:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )
        tail = deque(maxlen=6)
        for line in process.stdout:
            print(line, end="", flush=True)
            tail.append(line)
        return process.wait(), "".join(tail)
    p = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)
    return p.returncode, (p.stdout + p.stderr)


def build(root: Path, independent: bool):
    root.mkdir(parents=True)
    (root / "proj").mkdir()
    (root / "proj" / "__init__.py").write_text("")
    apps = ', "shop"' if independent else ""
    extra = 'AUTH_USER_MODEL = "shop.Member"' if independent else ""
    (root / "proj" / "settings.py").write_text(SETTINGS % {"apps": apps, "extra": extra})
    (root / "proj" / "urls.py").write_text(URLS % {"extra": ', path("shop/", include("shop.urls"))' if independent else ""})
    (root / "manage.py").write_text("import os, sys\nos.environ.setdefault('DJANGO_SETTINGS_MODULE','proj.settings')\n"
                                    "from django.core.management import execute_from_command_line\nexecute_from_command_line(sys.argv)\n")
    if independent:
        shop = root / "shop"; shop.mkdir(); (shop / "__init__.py").write_text("")
        (shop / "models.py").write_text("from django.contrib.auth.models import AbstractUser\nfrom django.db import models\n\n\nclass Member(AbstractUser):\n    pass\n\n\nclass Product(models.Model):\n    name = models.CharField(max_length=50)\n")
        (shop / "urls.py").write_text("from django.http import HttpResponse\nfrom django.urls import path\nurlpatterns = [path('', lambda r: HttpResponse('shop'))]\n")
    shutil.copytree(REPO / "ai", root / "ai", ignore=IGNORE)
    (root / "smoke.py").write_text(SMOKE)


def main():
    keep = "--keep" in sys.argv
    base = Path(tempfile.mkdtemp(prefix="ai_portability_"))
    ok = True
    for name, independent in (("new_project", False), ("independent_project", True)):
        root = base / name
        build(root, independent)
        if independent:
            run([sys.executable, "manage.py", "makemigrations", "shop"], root)
        steps = [("migrate", [sys.executable, "manage.py", "migrate", "-v", "0"]),
                 ("ai_setup", [sys.executable, "manage.py", "ai_setup"]),
                 ("makemigrations --check", [sys.executable, "manage.py", "makemigrations", "--check", "--dry-run"]),
                 ("routes", [sys.executable, "smoke.py"]),
                 ("ai tests", [sys.executable, "manage.py", "test", "ai.tests", "--noinput", "--verbosity=2",
                               # Browser tests require WealthFlow's frontend, which is not part of an AI-only copy.
                               "--exclude-tag=requires_host_ui"])]
        for label, cmd in steps:
            streaming = label == "ai tests"
            print(f"[{name}] {label}: RUNNING", flush=True)
            code, out = run(cmd, root, stream=streaming)
            tail = "\n".join(out.strip().splitlines()[-6:])
            print(f"[{name}] {label}: {'OK' if code == 0 else 'FAIL'}" +
                  ("\n" + textwrap.indent(tail, "    ") if tail and not streaming else ""))
            ok &= code == 0
    if not keep:
        shutil.rmtree(base, ignore_errors=True)
    print("PORTABILITY", "PASSED" if ok else "FAILED", "" if not keep else base)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
