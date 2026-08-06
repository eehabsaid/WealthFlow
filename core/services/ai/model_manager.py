"""
AI Model Management Layer.

Manages installed local models, version history (wealthflow-v1, wealthflow-v2), active model selection,
rollback operations, and automated pre-promotion benchmark triggers.
"""

from __future__ import annotations

import logging
from typing import Any
from core.models import AIModelVersion
from core.services.ai.training_backends import get_training_backend
from core.services.ai.dataset_engine import AIDatasetEngine
from core.services.ai.benchmark_engine import AIBenchmarkEngine

logger = logging.getLogger(__name__)


class AIModelManager:
    """
    Central manager for model version lifecycle, active deployment, and rollback.
    """

    @classmethod
    def get_active_model_version(cls) -> AIModelVersion:
        active = AIModelVersion.objects.filter(is_active=True).first()
        if not active:
            active = AIModelVersion.objects.create(
                version_name="wealthflow-v1",
                base_model="llama3:latest",
                training_backend="ollama",
                dataset_version="v1.0",
                benchmark_score=92.5,
                is_active=True,
            )
        return active

    @classmethod
    def get_all_model_versions(cls) -> list[AIModelVersion]:
        cls.get_active_model_version()
        return list(AIModelVersion.objects.all().order_by("-created_at"))

    @classmethod
    def promote_model_version(cls, version_name: str) -> AIModelVersion | None:
        target = AIModelVersion.objects.filter(version_name=version_name).first()
        if not target:
            return None

        AIModelVersion.objects.filter(is_active=True).update(is_active=False)
        target.is_active = True
        target.save(update_fields=["is_active"])
        return target

    @classmethod
    def rollback_model_version(cls, version_name: str) -> AIModelVersion | None:
        return cls.promote_model_version(version_name)

    @classmethod
    def trigger_fine_tuning(
        cls, base_model: str = "llama3:latest", backend_name: str = "ollama"
    ) -> dict[str, Any]:
        """
        Executes full Dataset-First Fine-Tuning Pipeline:
        1. Generates & validates SFT Dataset
        2. Delegates training to pluggable backend
        3. Creates candidate model version
        4. Runs Benchmark Pre-Promotion Suite
        5. Promotes ONLY if benchmark score > active production score
        """
        active = cls.get_active_model_version()

        # 1. Dataset Generation & Health Check
        ds_health = AIDatasetEngine.generate_sft_datasets()
        if not ds_health.get("ok"):
            return {
                "ok": False,
                "error": f"Dataset validation failed: {ds_health.get('error')}",
            }

        # 2. Increment Version Name
        v_count = AIModelVersion.objects.count() + 1
        output_version_name = f"wealthflow-v{v_count}"

        # 3. Invoke Pluggable Backend
        backend = get_training_backend(backend_name)
        train_res = backend.train_model(
            dataset_path=ds_health.get("file_path", ""),
            base_model_name=base_model,
            output_version_name=output_version_name,
        )

        if not train_res.get("ok"):
            return {
                "ok": False,
                "error": train_res.get("error", "Training failed"),
                "dataset_health": ds_health,
            }

        # 4. Create Candidate Model Version
        candidate = AIModelVersion.objects.create(
            version_name=output_version_name,
            base_model=base_model,
            training_backend=backend_name,
            dataset_version=f"v{v_count}.0",
            benchmark_score=0.0,
            is_active=False,
        )

        # 5. Run Pre-Promotion Benchmark Suite
        benchmark_report = AIBenchmarkEngine.evaluate_model_version(
            candidate_version=candidate, active_version=active
        )

        promoted = False
        if benchmark_report.passed_promotion_gate:
            cls.promote_model_version(output_version_name)
            promoted = True

        return {
            "ok": True,
            "candidate_version": candidate.to_dict(),
            "active_version": active.to_dict(),
            "benchmark_report": benchmark_report.to_dict(),
            "promoted_to_active": promoted,
            "dataset_health": ds_health,
        }
