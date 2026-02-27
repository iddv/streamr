"""
Economic configuration loaded from environment variables.
Task 5.4 — Req 14, Design §17
"""

import os
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class EconomicConfig:
    rate_per_gb: Decimal = Decimal("0.05")
    platform_margin: Decimal = Decimal("0.075")
    min_payout_threshold: Decimal = Decimal("0.01")

    @classmethod
    def from_env(cls) -> "EconomicConfig":
        return cls(
            rate_per_gb=Decimal(os.getenv("ECON_RATE_PER_GB", "0.05")),
            platform_margin=Decimal(os.getenv("ECON_PLATFORM_MARGIN", "0.075")),
            min_payout_threshold=Decimal(os.getenv("ECON_MIN_PAYOUT_THRESHOLD", "0.01")),
        )

    def to_dict(self) -> dict:
        return {
            "rate_per_gb": str(self.rate_per_gb),
            "platform_margin": str(self.platform_margin),
            "min_payout_threshold": str(self.min_payout_threshold),
        }


# Module-level singleton, initialised once at import time.
economic_config = EconomicConfig.from_env()
