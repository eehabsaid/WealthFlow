from django.db import models
from datetime import date, datetime


def _date_to_iso(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if value:
        return str(value)
    return ""


class AIKnowledgeEntry(models.Model):
    """
    Distilled, verified long-term domain knowledge entry.
    Stores business rules, codebase architecture, user preferences, and app evolution facts.
    """
    CATEGORY_CHOICES = [
        ("business_rule", "Business Rule & Calculation"),
        ("codebase_architecture", "Codebase Architecture & Services"),
        ("user_preference", "User Directive & Preference"),
        ("app_evolution", "Application Evolution & Feature"),
    ]

    key = models.CharField(max_length=255, unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="business_rule")
    title = models.CharField(max_length=255)
    content = models.TextField()
    confidence = models.FloatField(default=1.0)
    source = models.CharField(max_length=100, default="autonomous_learning")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def to_dict(self):
        return {
            "id": self.id,
            "key": self.key,
            "category": self.category,
            "title": self.title,
            "content": self.content,
            "confidence": self.confidence,
            "source": self.source,
            "is_active": self.is_active,
            "created_at": _date_to_iso(self.created_at),
            "updated_at": _date_to_iso(self.updated_at),
        }


class AIModelVersion(models.Model):
    """
    Stores local AI model versions, training metadata, and active status.
    """
    version_name = models.CharField(max_length=100, unique=True)
    base_model = models.CharField(max_length=100, default="qwen2.5:3b")
    training_backend = models.CharField(max_length=50, default="ollama")
    dataset_version = models.CharField(max_length=50, default="v1.0")
    benchmark_score = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=False)
    metadata_json = models.TextField(default="{}")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def to_dict(self):
        return {
            "id": self.id,
            "version_name": self.version_name,
            "base_model": self.base_model,
            "training_backend": self.training_backend,
            "dataset_version": self.dataset_version,
            "benchmark_score": self.benchmark_score,
            "is_active": self.is_active,
            "created_at": _date_to_iso(self.created_at),
        }


class AIBenchmarkReport(models.Model):
    """
    Stores 7-dimension benchmark evaluation results comparing candidate models vs active production.
    """
    model_version = models.ForeignKey(AIModelVersion, on_delete=models.CASCADE, related_name="benchmarks")
    business_analysis_score = models.FloatField(default=0.0)
    financial_reasoning_score = models.FloatField(default=0.0)
    architecture_score = models.FloatField(default=0.0)
    code_understanding_score = models.FloatField(default=0.0)
    feature_suggestion_score = models.FloatField(default=0.0)
    hallucination_resistance_score = models.FloatField(default=0.0)
    instruction_following_score = models.FloatField(default=0.0)
    overall_score = models.FloatField(default=0.0)
    passed_promotion_gate = models.BooleanField(default=False)
    evaluation_details_json = models.TextField(default="{}")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def to_dict(self):
        return {
            "id": self.id,
            "model_version": self.model_version.version_name,
            "overall_score": round(self.overall_score, 2),
            "passed_promotion_gate": self.passed_promotion_gate,
            "scores": {
                "business_analysis": round(self.business_analysis_score, 2),
                "financial_reasoning": round(self.financial_reasoning_score, 2),
                "architecture": round(self.architecture_score, 2),
                "code_understanding": round(self.code_understanding_score, 2),
                "feature_suggestions": round(self.feature_suggestion_score, 2),
                "hallucination_resistance": round(self.hallucination_resistance_score, 2),
                "instruction_following": round(self.instruction_following_score, 2),
            },
            "created_at": _date_to_iso(self.created_at),
        }
