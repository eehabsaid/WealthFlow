from django.test import TestCase

from core.authentication.services.member_role import ensure_member_role
from core.constants import PAGE_PERMISSION_CHOICES
from core.models import Role, RolePermission


class MemberRoleBudgetKeysTest(TestCase):
    def test_new_keys_are_valid_page_permission_choices(self):
        valid = {key for key, _label in PAGE_PERMISSION_CHOICES}
        self.assertIn("budgets", valid)
        self.assertIn("import_data", valid)

    def test_fresh_member_role_includes_budgets_and_import_data(self):
        Role.objects.all().delete()
        role = ensure_member_role(Role, RolePermission)
        keys = set(RolePermission.objects.filter(role=role).values_list("key", flat=True))
        self.assertIn("budgets", keys)
        self.assertIn("import_data", keys)
