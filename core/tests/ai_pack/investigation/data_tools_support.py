"""Shared base for the data tools tests."""



from django.test import TestCase

from ai.services.investigation import data_tools as dt

from core.tests.ai_pack.investigation.support import make_user, seed_tenant


class DataToolsBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a, cls.b = make_user("tenant_a"), make_user("tenant_b")
        seed_tenant(cls.a, "A", expenses=3, amount="10.00")
        seed_tenant(cls.b, "B", expenses=5, amount="100.00")

    def q(self, user, **params):
        return dt.query(user, params)
