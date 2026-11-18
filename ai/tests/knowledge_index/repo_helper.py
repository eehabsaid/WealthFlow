"""A miniature WealthFlow-shaped repository for knowledge-index tests (models, services, views, routes, tests, script-global JS,
template, locale files, plus files that must never be indexed)."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from django.test import TestCase, override_settings

CRLF = True   # set to True to run the whole suite against Windows-style line endings
FILES = {
    "core/models.py": '''from django.conf import settings
from django.db import models


class Currency(models.Model):
    code = models.CharField(max_length=3)


class Account(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    balance = models.DecimalField(max_digits=14, decimal_places=2)


class Expense(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
''',
    "core/services/mirror.py": '''"""Mirror engine: an expense moves the account balance."""
from core.models import Account


def apply_balance(account, amount):
    """Subtract amount from the account balance."""
    account.balance = account.balance - amount
    return account


def sync_mirror(expense):
    """Keep the account balance in step with the expense."""
    return apply_balance(expense.account, expense.amount)
''',
    "core/services/net_worth.py": '''from core.models import Account


class NetWorthService:
    """Calculates net worth as the sum of all account balances of one owner."""

    def total(self, owner):
        rows = Account.objects.filter(owner=owner)
        return sum(a.balance for a in rows)
''',
    "core/views.py": '''from core.services.net_worth import NetWorthService


class NetWorthView:
    def get(self, request):
        return {"total": NetWorthService().total(request.user)}
''',
    "core/urls.py": '''from django.urls import path
from core.views import NetWorthView

urlpatterns = [
    path("api/net-worth/", NetWorthView.as_view(), name="net_worth"),
    path("api/expenses/<int:pk>/", NetWorthView.as_view(), name="expense_detail"),
]
''',
    "core/tests/__init__.py": "",
    "core/tests/test_net_worth.py": '''from core.services.net_worth import NetWorthService


class NetWorthTests:
    def test_total(self):
        assert NetWorthService().total(None) == 0
''',
    "core/settings_secret.py": 'SECRET_KEY = "super-secret-value-123456"\nAPI_TOKEN = "tok_live_abcdef0123456789"\nDEBUG = True\n',
    "static/js/utils/format.js": '''var WF_CURRENCY = "EGP";

function formatMoney(value) {
  return Number(value).toFixed(2);
}
''',
    "static/js/net_worth/page.js": '''async function loadNetWorth() {
  const res = await fetch(`/api/net-worth/`);
  renderNetWorth(await res.json());
}

function renderNetWorth(data) {
  const text = formatMoney(data.total) + " " + WF_CURRENCY;
  const label = "function fake() {}";   // a string, not a definition
  document.getElementById("nwValue").textContent = text + label;
}
''',
    "static/js/net_worth/other.js": '''window.refreshNetWorth = function () {
  loadNetWorth();
};

function showNetWorthAgain(d) {
  renderNetWorth(d);
}
''',
    "templates/index.html": '''<html><body>
<button id="nwBtn" data-i18n="nw_title" onclick="refreshNetWorth()">Net worth</button>
<script src="/static/js/utils/format.js"></script>
<script src="/static/js/net_worth/page.js"></script>
</body></html>
''',
    "static/css/app.css": ".nw-card { color: var(--wf-primary); }\n.nw-card .title { font-weight: 600; }\n",
    "static/i18n/en.json": json.dumps({"nw_title": "Net worth", "nw_hint": "Sum of all balances"}, indent=4) + "\n",
    "static/i18n/ar.json": json.dumps({"nw_title": "صافي الثروة", "nw_hint": "مجموع الأرصدة"}, ensure_ascii=False, indent=4) + "\n",
    "static/i18n/fr.json": json.dumps({"nw_title": "Valeur nette", "nw_hint": "Somme des soldes"}, indent=4) + "\n",
    "static/i18n/de.json": json.dumps({"nw_title": "Nettovermögen"}, indent=4) + "\n",
    ".env": "SECRET=never-index-this-1234567890\n",
    "node_modules/pkg/index.js": "function vendorFn() {}\n",
    "db.sqlite3": "SQLite format 3\0 private rows",
}


def build_repo(root: Path) -> None:
    for rel, text in FILES.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.replace("\n", "\r\n").encode("utf-8") if CRLF else text.encode("utf-8"))


class RepoTestCase(TestCase):
    """Each test gets its own copy of the fixture repo and its own index file."""

    engine = "auto"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="kidx_"))
        self.root = self.tmp / "repo"
        build_repo(self.root)
        self.addCleanup(shutil.rmtree, self.tmp, True)
        override = override_settings(AI_KNOWLEDGE_ROOT=str(self.root), AI_KNOWLEDGE_INDEX_PATH=str(self.tmp / "idx.sqlite3"),
                                     AI_KNOWLEDGE_JS_ENGINE=self.engine)
        override.enable()
        self.addCleanup(override.disable)
        from unittest import mock

        from ai.services.knowledge_index import session, vectors

        patch = mock.patch.object(vectors.embeddings, "_embed_query", return_value=None)   # tests never call Ollama; keyword mode unless a test opts in
        patch.start()
        self.addCleanup(patch.stop)
        session.reset_throttle()
        self.addCleanup(session.reset_throttle)

    def index(self, **kw):
        from ai.services.knowledge_index import indexer

        return indexer.refresh(**kw)

    def conn(self):
        from ai.services.knowledge_index import store

        conn = store.connect()
        self.addCleanup(conn.close)
        return conn

    def write(self, rel: str, text: str):
        target = self.root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.replace("\n", "\r\n").encode("utf-8") if CRLF else text.encode("utf-8"))
