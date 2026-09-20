"""Read/write filtering for /api/settings/ (see core/constants/settings_access.py)."""

from core.authentication.utils.auth_utils import effective_permission_keys, user_is_sysadmin
from core.constants.settings_access import (
    GLOBAL_KEY_PERMISSIONS,
    MEMBER_READABLE_SETTING_KEYS,
    SECRET_KEY_MARKERS,
)
from core.constants.user_scoped_settings import ACTIVE_LANGUAGE_KEY, USER_SCOPED_SETTING_KEYS


def is_secret_key(key):
    lowered = key.lower()
    return any(marker in lowered for marker in SECRET_KEY_MARKERS)


def _required_permission(key):
    for prefix, permission in GLOBAL_KEY_PERMISSIONS:
        if key.startswith(prefix):
            return permission
    return None


def _is_own_key(key):
    return key == ACTIVE_LANGUAGE_KEY or key in USER_SCOPED_SETTING_KEYS


class SettingsAccess:
    """Per-request decision helper for one authenticated user."""

    def __init__(self, user):
        self.sysadmin = user_is_sysadmin(user)
        self.permissions = set() if self.sysadmin else effective_permission_keys(user)

    def can_write(self, key):
        if self.sysadmin or _is_own_key(key):
            return True
        return _required_permission(key) in self.permissions

    def can_read(self, key):
        if self.can_write(key):
            return True
        return key in MEMBER_READABLE_SETTING_KEYS

    def filter_for_read(self, resolved):
        """Whitelist the resolved settings; secrets become <key>_is_set flags."""
        visible = {}
        for key, value in resolved.items():
            if not self.can_read(key):
                continue
            if is_secret_key(key):
                visible[f"{key}_is_set"] = "true" if value else "false"
            else:
                visible[key] = value
        return visible
