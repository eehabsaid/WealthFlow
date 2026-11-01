# Security and multi-tenancy
- Every user-owned row has an `owner` FK. Query with `Model.objects.filter(owner=request.user)` or the helpers in `core/validators/ownership.py` (`_owned_queryset`, `_owned_object_or_404`, `_child_owned_*`). No staff or superuser bypass.
- Child rows inherit ownership through their parent (e.g. salary entries via `company__owner`).
- Start every API view with `_api_auth_required(request)`. CSRF is on everywhere except the Paymob webhook. Login attempts use django-axes.
- Settings and secrets: AI provider keys are encrypted (`credential_encryption.py`); never log or return them. `.env` and `db.sqlite3` are never edited.
- Non-admins only get a whitelist from `/api/settings/`. Source-code tools of the AI are sysadmin-only.
- Every security-relevant change needs a test proving user A cannot read or change user B's data (pattern in the tests of `core/tests/ai/test_ai_chat_manage.py`).
