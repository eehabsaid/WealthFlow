"""Users for knowledge-index tests."""

from django.contrib.auth import get_user_model

from ai.tests.support import grant_ai_workspace_access, make_sysadmin


def make_user(username: str, sysadmin: bool = False):
    user = get_user_model().objects.create_user(username=username, password="pw-test-12345", email=f"{username}@example.test")
    if sysadmin:
        make_sysadmin(user)
    grant_ai_workspace_access(user)
    return user
