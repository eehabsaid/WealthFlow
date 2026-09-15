"""Shared helper for non-billing test suites that need a user to pass the
AI Workplace plan gate (`feature_required("allows_ai_workspace")`) so they
can exercise AI endpoint behavior without also setting up billing state.
"""

from django.utils import timezone

from core.models import Plan, Subscription

_AI_ACCESS_PLAN_CODE = "test_ai_access_plan"


def grant_ai_workspace_access(user) -> Subscription:
    """Idempotent: safe to call once per user even across multiple tests
    in the same TestCase, and reuses one shared Plan row across callers."""
    plan, _ = Plan.objects.get_or_create(
        code=_AI_ACCESS_PLAN_CODE,
        defaults={"name": "Test AI Access Plan", "sort_order": 99, "allows_ai_workspace": True},
    )
    if not plan.allows_ai_workspace:
        plan.allows_ai_workspace = True
        plan.save(update_fields=["allows_ai_workspace"])

    subscription, _ = Subscription.objects.update_or_create(
        owner=user,
        defaults={
            "plan": plan,
            "status": "active",
            "current_period_end": timezone.now() + timezone.timedelta(days=30),
        },
    )
    return subscription
