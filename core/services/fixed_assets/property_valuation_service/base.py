from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.models import FixedAsset, RealEstateDetails


@dataclass
class PropertyValuationResult:
    processed_assets: int = 0
    updated_assets: int = 0
    skipped_assets: int = 0

    def to_dict(self):
        return {
            "processed_assets": self.processed_assets,
            "updated_assets": self.updated_assets,
            "skipped_assets": self.skipped_assets,
        }


class BasePropertyValuationProvider:
    name = "base"

    def estimate(self, asset: FixedAsset, details: RealEstateDetails) -> Optional[float]:
        return None
