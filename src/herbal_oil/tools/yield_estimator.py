"""Yield estimator tool.

Uses an embedded heuristic model (literature-typical yield ranges per
method + herb family) to estimate essential-oil yield (% w/w) and an aroma-
preservation index. Inputs are validated; missing herb family falls back to a
generic envelope with an `inferred` flag. This is deterministic arithmetic,
not an LLM hallucination, so numbers are reproducible and auditable.
"""
from __future__ import annotations

from typing import Any

from ..core.base_tool import BaseTool

# Baseline yields (% w/w, dry-basis) typical of mature, well-prepped material.
BASELINE_YIELDS: dict[str, dict[str, float]] = {
    "lavender": {"steam": 1.2, "hydro": 1.0, "sfe_co2": 2.2, "microwave": 1.6},
    "peppermint": {"steam": 1.5, "hydro": 1.3, "sfe_co2": 2.6, "microwave": 1.9},
    "clove": {"steam": 14.0, "hydro": 12.0, "sfe_co2": 18.0, "microwave": 15.5},
    "lemongrass": {"steam": 0.8, "hydro": 0.7, "sfe_co2": 1.4, "microwave": 1.1},
    "rosemary": {"steam": 1.4, "hydro": 1.2, "sfe_co2": 2.4, "microwave": 1.8},
}
GENERIC_YIELD = {"steam": 1.0, "hydro": 0.9, "sfe_co2": 1.8, "microwave": 1.3}
METHOD_KEYS = {"steam": "steam", "hydrodistillation": "hydro", "hydro": "hydro",
               "sfe_co2": "sfe_co2", "sfe-co2": "sfe_co2", "supercritical co2": "sfe_co2",
               "microwave": "microwave", "microwave-assisted": "microwave"}

# Thermal sensitivity (0=safe, 1=highly thermolabile) drives aroma index.
THERMAL_SENSITIVITY = {"steam": 0.45, "hydro": 0.60, "sfe_co2": 0.05, "microwave": 0.35}


class YieldEstimatorTool(BaseTool):
    name = "yield_estimator"
    description = "Estimate essential-oil yield (% w/w) and aroma-preservation index for an herb+method from literature-typical baselines."
    parameters = {
        "type": "object",
        "properties": {
            "herb": {"type": "string", "minLength": 2},
            "method": {"type": "string", "description": "steam | hydrodistillation | sfe_co2 | microwave"},
            "plant_water_ratio": {"type": "number", "minimum": 0.05, "maximum": 2.0,
                                  "description": "g dry-plant per g water (higher = denser charge)"},
            "duration_minutes": {"type": "number", "minimum": 10, "maximum": 600},
        },
        "required": ["herb", "method"],
        "additionalProperties": False,
    }

    def run(self, herb: str, method: str, plant_water_ratio: float = 0.25,
            duration_minutes: float = 120.0, **_: Any) -> dict[str, Any]:
        key = herb.strip().lower()
        known = next((k for k in BASELINE_YIELDS if k in key or key in k), None)
        yields = BASELINE_YIELDS[known] if known else GENERIC_YIELD
        inferred = known is None
        mkey = METHOD_KEYS.get(method.strip().lower(), "steam")
        base = yields.get(mkey, yields["steam"])

        # Empirical multiplicative factors (kept simple and auditable).
        # ratio factor: under-charging reduces yield; over-charging saturates.
        ratio_factor = min(1.10, 0.7 + 1.2 * max(0.05, plant_water_ratio))
        # duration factor: ~saturating curve to 1.0 around 150 min.
        duration_factor = min(1.05, 1 - 0.5 * (1 - min(duration_minutes / 150.0, 1.5)))
        estimated_yield = round(base * ratio_factor * duration_factor, 3)

        # Aroma preservation index: 1 - thermal_sensitivity, scaled by duration.
        ts = THERMAL_SENSITIVITY.get(mkey, 0.5)
        heat_penalty = ts * min(1.0, max(0.0, (duration_minutes - 120.0) / 180.0))
        aroma_index = round(max(0.0, 1.0 - heat_penalty), 3)

        return {
            "herb": herb,
            "method": mkey,
            "estimated_yield_pct": estimated_yield,
            "baseline_yield_pct": base,
            "aroma_preservation_index": aroma_index,
            "factors": {"ratio_factor": round(ratio_factor, 3), "duration_factor": round(duration_factor, 3)},
            "inferred": inferred,
            "source": "literature-typical baselines (YieldEstimatorTool)",
        }


__all__ = ["YieldEstimatorTool", "BASELINE_YIELDS"]