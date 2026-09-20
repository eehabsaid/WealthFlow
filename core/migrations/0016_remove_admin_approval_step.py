from datetime import timedelta

from django.db import migrations, models
from django.utils import timezone

from core.authentication.services.member_role import ensure_member_role
from core.constants import TRIAL_DAYS_DEFAULT

REMOVED_TEMPLATE_KEYS = ["admin_approval_request", "account_approved", "account_rejected"]


def activate_users_pending_admin_approval(apps, schema_editor):
    """Users who verified their email but were still waiting for admin
    approval become active: same end state the new verification flow gives."""
    UserProfile = apps.get_model("core", "UserProfile")
    Role = apps.get_model("core", "Role")
    RolePermission = apps.get_model("core", "RolePermission")
    UserRole = apps.get_model("core", "UserRole")
    Plan = apps.get_model("core", "Plan")
    Subscription = apps.get_model("core", "Subscription")

    pending = list(UserProfile.objects.filter(account_status="pending_admin_approval").select_related("user"))
    if not pending:
        return
    member_role = ensure_member_role(Role, RolePermission)
    plan = Plan.objects.filter(is_active=True).order_by("sort_order", "id").first()
    now = timezone.now()
    for profile in pending:
        user = profile.user
        profile.account_status = "active"
        profile.email_verified = True
        profile.approved_at = now
        profile.save(update_fields=["account_status", "email_verified", "approved_at"])
        user.is_active = True
        user.save(update_fields=["is_active"])
        UserRole.objects.get_or_create(user=user, role=member_role)
        if plan is not None:
            Subscription.objects.get_or_create(
                owner=user,
                defaults={"plan": plan, "status": "trialing", "trial_end": now + timedelta(days=TRIAL_DAYS_DEFAULT)},
            )


def delete_approval_email_templates(apps, schema_editor):
    apps.get_model("core", "EmailTemplate").objects.filter(key__in=REMOVED_TEMPLATE_KEYS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_repoint_currency_fks'),
    ]

    operations = [
        migrations.RunPython(activate_users_pending_admin_approval, migrations.RunPython.noop),
        migrations.RunPython(delete_approval_email_templates, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='authtoken',
            name='purpose',
            field=models.CharField(choices=[('email_verification', 'Email Verification'), ('password_reset', 'Password Reset')], max_length=50),
        ),
    ]
