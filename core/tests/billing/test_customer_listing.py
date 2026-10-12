"""Sysadmin customer list: pagination, bounded query count, newest-first invoices and lazy 'show more' invoices."""

from datetime import timedelta
from decimal import Decimal

from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.models import Invoice, Subscription

from .customer_admin_support import CustomerAdminBase, User

LIST = "/api/settings/billing/customers/"


class CustomerListingTestCase(CustomerAdminBase):
    def _make_users(self, n):
        users = [User.objects.create_user(username=f"pg_user_{i:03d}", password="pw123456", email=f"pg{i}@x.io") for i in range(n)]
        for u in users:
            Subscription.objects.create(owner=u, plan=self.basic, status="trialing", trial_end=self.now + timedelta(days=3))
        return users

    def _invoices(self, user, n):
        sub = Subscription.objects.get(owner=user)
        return [
            Invoice.objects.create(
                owner=user, subscription=sub, plan=self.pro, amount=Decimal("10.00") + i, currency=self.currency,
                status="pending", period_start=self.now, period_end=self.now + timedelta(days=30),
                issued_at=self.now + timedelta(minutes=i),
            )
            for i in range(n)
        ]

    def test_first_page_is_25_and_reports_totals(self):
        self._make_users(30)
        res = self.client.get(LIST).json()
        self.assertEqual((len(res["customers"]), res["total"], res["page"], res["page_size"]), (25, 31, 1, 25))
        self.assertTrue(res["has_more"])
        usernames = [c["username"] for c in res["customers"]]
        self.assertEqual(usernames, sorted(usernames))

    def test_pages_cover_every_user_exactly_once(self):
        self._make_users(30)
        seen = []
        for page in (1, 2):
            res = self.client.get(f"{LIST}?page={page}&page_size=20").json()
            seen += [c["user_id"] for c in res["customers"]]
        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(len(seen), 31)
        self.assertFalse(self.client.get(f"{LIST}?page=2&page_size=20").json()["has_more"])

    def test_bad_paging_values_are_clamped_not_errors(self):
        self._make_users(3)
        for qs in ("page=abc", "page=-4", "page=999", "page_size=0", "page_size=100000", "page_size=x"):
            res = self.client.get(f"{LIST}?{qs}")
            self.assertEqual(res.status_code, 200, qs)
            self.assertLessEqual(len(res.json()["customers"]), 100)
        self.assertEqual(self.client.get(f"{LIST}?page_size=100000").json()["page_size"], 100)
        self.assertEqual(self.client.get(f"{LIST}?page=999").json()["page"], 1)   # clamped to the last page

    def test_search_paginates_and_counts_only_matches(self):
        self._make_users(30)
        res = self.client.get(f"{LIST}?q=pg_user_01&page_size=5").json()
        self.assertEqual((res["total"], len(res["customers"])), (10, 5))
        self.assertTrue(all("pg_user_01" in c["username"] for c in res["customers"]))
        self.assertEqual(self.client.get(f"{LIST}?q=pg1%40x.io").json()["total"], 1)   # e-mail match

    def test_query_count_does_not_grow_with_users_or_invoices(self):
        users = self._make_users(25)
        for u in users[:10]:
            self._invoices(u, 3)
        with CaptureQueriesContext(connection) as ctx:
            res = self.client.get(f"{LIST}?page_size=25").json()
        self.assertEqual(len(res["customers"]), 25)
        listing_queries = [q for q in ctx.captured_queries if "billing_" in q["sql"] or "auth_user" in q["sql"]]
        self.assertLessEqual(len(listing_queries), 8, [q["sql"][:90] for q in listing_queries])

    def test_each_customer_carries_only_newest_ten_invoices_but_the_true_count(self):
        user = self._make_users(1)[0]
        made = self._invoices(user, 14)
        row = next(c for c in self.client.get(f"{LIST}?q={user.username}").json()["customers"] if c["user_id"] == user.id)
        self.assertEqual(row["invoice_count"], 14)
        self.assertEqual([i["id"] for i in row["invoices"]], [i.id for i in reversed(made)][:10])

    def test_invoices_endpoint_pages_newest_first(self):
        user = self._make_users(1)[0]
        made = self._invoices(user, 14)
        newest_first = [i.id for i in reversed(made)]
        url = f"/api/settings/billing/customers/{user.id}/invoices/"
        first = self.client.get(f"{url}?offset=0&limit=10").json()
        rest = self.client.get(f"{url}?offset=10&limit=10").json()
        self.assertEqual([i["id"] for i in first["invoices"]], newest_first[:10])
        self.assertTrue(first["has_more"])
        self.assertEqual([i["id"] for i in rest["invoices"]], newest_first[10:])
        self.assertEqual((rest["total"], rest["has_more"]), (14, False))
        self.assertEqual(self.client.get(f"{url}?limit=9999").json()["offset"], 0)
        self.assertEqual(self.client.get(f"{url}?offset=zzz&limit=qq").status_code, 200)

    def test_invoices_endpoint_is_sysadmin_only_and_scoped_to_one_customer(self):
        user = self._make_users(1)[0]
        other = User.objects.create_user(username="pg_other", password="pw123456")
        Subscription.objects.create(owner=other, plan=self.basic, status="trialing", trial_end=self.now + timedelta(days=3))
        self._invoices(other, 2)
        self.assertEqual(self.client.get(f"/api/settings/billing/customers/{user.id}/invoices/").json()["total"], 0)
        self.assertEqual(self.client.get("/api/settings/billing/customers/999999/invoices/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/settings/billing/customers/{self.admin.id}/invoices/").status_code, 404)
        self.client.force_login(user)
        self.assertIn(self.client.get(f"/api/settings/billing/customers/{other.id}/invoices/").status_code, (401, 403))

    def test_action_response_still_returns_a_full_customer_row(self):
        res = self._customer(action="suspend").json()["customer"]
        self.assertEqual(res["subscription"]["status"], "suspended")
        self.assertIn("invoice_count", res)
