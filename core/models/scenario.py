from django.db import models
from datetime import date, datetime


def _date_to_iso(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if value:
        return str(value)
    return ""


class Scenario(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_baseline_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_baseline_pinned": self.is_baseline_pinned,
            "created_at": _date_to_iso(self.created_at),
            "updated_at": _date_to_iso(self.updated_at),
            "events": [ev.to_dict() for ev in self.events.all()],
        }


class ScenarioEvent(models.Model):
    EVENT_TYPES = [
        ("house", "Buy House"),
        ("car", "Buy Car"),
        ("salary_change", "Salary Change"),
        ("marriage", "Marriage"),
        ("child", "Child"),
        ("retirement", "Retirement"),
        ("inheritance", "Inheritance"),
        ("medical", "Medical Event"),
        ("business", "Start Business"),
        ("job_loss", "Job Loss"),
    ]

    scenario = models.ForeignKey(
        Scenario,
        on_delete=models.CASCADE,
        related_name="events",
    )
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    event_date = models.DateField()
    params = models.JSONField(default=dict, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "event_date", "id"]

    def to_dict(self):
        return {
            "id": self.id,
            "scenario_id": self.scenario_id,
            "event_type": self.event_type,
            "event_date": _date_to_iso(self.event_date),
            "params": self.params or {},
            "order": self.order,
            "created_at": _date_to_iso(self.created_at),
        }
