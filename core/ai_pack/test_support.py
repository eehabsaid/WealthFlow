"""Test hooks WealthFlow gives the portable ai tests (settings.AI_TEST_SUPPORT)."""
from core.tests.billing.test_support import grant_ai_workspace_access  # noqa: F401

__all__ = ["grant_ai_workspace_access"]


def make_sysadmin(user):
    from core.authentication.services import AuthWorkflowService
    profile = AuthWorkflowService.get_profile(user)
    profile.is_sysadmin = True
    profile.save(update_fields=["is_sysadmin"])
    return user
