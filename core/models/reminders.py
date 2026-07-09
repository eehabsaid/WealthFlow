from django.db import models
from django.utils import timezone

from core.constants import REMINDER_TYPE_CHOICES, SALARY_TRIGGER_CHOICES

class ReminderRule(models.Model):
    """Fully configurable reminder rule — no hardcoded values."""

    name = models.CharField(max_length=200)
    rule_type = models.CharField(
        max_length=50, choices=REMINDER_TYPE_CHOICES, default="cert_maturity"
    )
    is_active = models.BooleanField(default=True)

    # Certificate maturity fields
    days_before = models.IntegerField(
        default=30, help_text="Days before expiry (cert_maturity)"
    )

    # Salary fields
    salary_trigger = models.CharField(
        max_length=50,
        choices=SALARY_TRIGGER_CHOICES,
        default="day_of_month",
        blank=True,
    )
    salary_day = models.IntegerField(
        default=25, help_text="Trigger value for salary reminder"
    )
    salary_message = models.CharField(
        max_length=300,
        blank=True,
        default="Salary reminder: check if this month has been paid",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["rule_type", "name"]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "rule_type": self.rule_type,
            "rule_type_label": dict(REMINDER_TYPE_CHOICES).get(
                self.rule_type, self.rule_type
            ),
            "is_active": self.is_active,
            "days_before": self.days_before,
            "salary_trigger": self.salary_trigger,
            "salary_trigger_label": dict(SALARY_TRIGGER_CHOICES).get(
                self.salary_trigger, ""
            ),
            "salary_day": self.salary_day,
            "salary_message": self.salary_message,
            "created_at": self.created_at.strftime("%Y-%m-%d"),
        }

    def __str__(self):
        return f"{self.name} ({self.rule_type})"


class ReminderLog(models.Model):
    """Records each time a reminder was shown to avoid daily duplicates."""

    rule = models.ForeignKey(
        ReminderRule, on_delete=models.CASCADE, related_name="logs"
    )
    related_model = models.CharField(max_length=100, blank=True)
    related_id = models.IntegerField(null=True, blank=True)
    fired_on = models.DateField(default=timezone.localdate)
    message = models.TextField(blank=True)

    class Meta:
        unique_together = ["rule", "related_model", "related_id", "fired_on"]
        ordering = ["-fired_on"]

    def to_dict(self):
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "rule_name": self.rule.name,
            "related_model": self.related_model,
            "related_id": self.related_id,
            "fired_on": self.fired_on.isoformat(),
            "message": self.message,
        }
