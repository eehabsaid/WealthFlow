"""Shared constants for the auth workflow service."""

PROFILE_STATUS_ERROR_KEYS = {
    "pending_email_verification": "auth_status_verify_email",
    "pending_admin_approval": "auth_status_pending_admin_approval",
    "rejected": "auth_status_rejected",
    "disabled": "auth_status_disabled",
}
