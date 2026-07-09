from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=200, blank=True)
    avatar_b64 = models.TextField(blank=True, default="")
    bio = models.TextField(blank=True)
    birthday = models.DateField(null=True, blank=True)
    email_verified = models.BooleanField(default=True)
    account_status = models.CharField(max_length=50, default="active")
    status_reason = models.TextField(blank=True, default="")
    preferred_language = models.CharField(max_length=10, blank=True, default="")
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_user_profiles",
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rejected_user_profiles",
    )
    disabled_at = models.DateTimeField(null=True, blank=True)
    disabled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="disabled_user_profiles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def avatar_url(self):
        """Returns the base64 data URL directly — no file system needed."""
        return self.avatar_b64 if self.avatar_b64 else None

    def display_name(self):
        return self.full_name or self.user.get_full_name() or self.user.username

    def to_dict(self):
        return {
            "full_name": self.full_name,
            "avatar_url": self.avatar_url(),
            "bio": self.bio,
            "birthday": self.birthday.isoformat() if self.birthday else "",
            "email_verified": self.email_verified,
            "account_status": self.account_status,
            "status_reason": self.status_reason,
            "preferred_language": self.preferred_language,
        }

    def __str__(self):
        return f"Profile({self.user.username})"


AUTH_ACCOUNT_STATUS_CHOICES = [
    ("pending_email_verification", "Pending Email Verification"),
    ("pending_admin_approval", "Pending Administrator Approval"),
    ("active", "Active"),
    ("rejected", "Rejected"),
    ("disabled", "Disabled"),
]

AUTH_TOKEN_PURPOSE_CHOICES = [
    ("email_verification", "Email Verification"),
    ("password_reset", "Password Reset"),
    ("admin_approve", "Administrator Approval"),
    ("admin_reject", "Administrator Rejection"),
]

AUTH_AUDIT_EVENT_CHOICES = [
    ("registration", "Registration"),
    ("email_verified", "Email Verified"),
    ("admin_approved", "Administrator Approved"),
    ("admin_rejected", "Administrator Rejected"),
    ("account_disabled", "Account Disabled"),
    ("account_reenabled", "Account Re-enabled"),
    ("password_reset_requested", "Password Reset Requested"),
    ("password_reset_completed", "Password Reset Completed"),
]


class AuthToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="auth_tokens")
    purpose = models.CharField(max_length=50, choices=AUTH_TOKEN_PURPOSE_CHOICES)
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def is_expired(self):
        return bool(self.expires_at and timezone.now() >= self.expires_at)

    def is_usable(self):
        return self.used_at is None and not self.is_expired()

    def __str__(self):
        return f"AuthToken({self.user.username}, {self.purpose})"


class AuthAuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="auth_audit_logs")
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auth_audit_actions",
    )
    event_type = models.CharField(max_length=50, choices=AUTH_AUDIT_EVENT_CHOICES)
    details = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"AuthAuditLog({self.user.username}, {self.event_type})"
