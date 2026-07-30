"""core-analysis agent (Step 3).

The domain engine: selects an extraction method + parameters, runs the GC-MS
profile and yield-estimator tools, assesses aroma preservation, and applies
ISO/pharmacopoeia standardization. Produces best/base/worst scenarios. In the
comparison intent the runner invokes this agent twice (the second pass reads
``iteration`` so the agent can tag the object variant).
"""
from __future__ import annotations

import re
from typing import Any

from ..core.base_agent import AgentResult, BaseAgent

HERB_RE = re.compile(
    r"\b(lavender|peppermint|clove|lemongrass|rosemary|basil|oregano|thyme|mint|"
    r"eucalyptus|ginger|chamchamile|chamomile|jasmine|sage|cinnamon|citronella)\b",
    re.I,
)


class CoreAnalysisAgent(BaseAgent):
    name = "core-analysis"
    persona = "essential-oil extraction & aromatic-chemistry engineer"
    description = "Optimize method, parameters, yield & aroma profile, preserving volatiles per ISO standards."
    tool_names = ("gcms_profile", "yield_estimator", "knowledge_query")
    output_schema = {
        "type": "object",
        "properties": {
            "herb": {"type": "string"},
            "method": {"type": "string"},
            "parameters": {"type": "object"},
            "pretreatment": {"type": "object"},
            "gcms_profile": {"type": "array", "items": {"type": "object"}},
            "yield_pct": {"type": "number"},
            "aroma_preservation": {"type": "object"},
            "standardization": {"type": "object"},
            "scenarios": {"type": "object"},
        },
        "required": ["herb", "method", "parameters", "aroma_preservation", "standardization"],
    }

    def solve(self, state: Any, iteration: int = 0, **_: Any) -> AgentResult:
        req = state.requirements or {}
        obj = req.get("object", "essential oil extraction")
        herb_m = HERB_RE.search(obj) or HERB_RE.search(state.user_input or "")
        herb = herb_m.group(1).lower() if herb_m else "unknown-herb"

        # Method selection heuristic: thermo-labile herbs -> SFE-CO2; high-value
        # aroma herbs -> steam; high-yield (clove) -> steam is fine.
        thermolabile = {"lavender", "jasmine", "chamomile"}
        high_yield = {"clove", "cinnamon"}
        if herb in thermolabile:
            method = "sfe_co2"
        elif herb in high_yield:
            method = "steam"
        else:
            method = "steam"

        parameters = {
            "temperature_C": 40 if method == "sfe_co2" else 100,
            "pressure_bar": 250 if method == "sfe_co2" else 1.0,
            "time_min": 90 if method == "sfe_co2" else 150,
            "plant_water_ratio": 0.25,
            "particle_size_mm": 2.0,
            "co_flow": "1.5 L/min CO2" if method == "sfe_co2" else "n/a",
        }
        pretreatment = {
            "drying": "shade-dry to ~10% moisture, T<35C",
            "comminution": "grind to ~2 mm to rupture oil glands without heat",
        }

        limitations: list[str] = []
        gcms: list[dict[str, Any]] = []
        try:
            res = self.use_tool("gcms_profile", herb=herb, volatility_budget=95.0 if method == "sfe_co2" else 70.0)
            gcms = res.get("result", {}).get("chemotype", [])
            if res.get("result", {}).get("inferred"):
                limitations.append(f"GC-MS profile inferred (herb '{herb}' not in reference table)")
        except Exception as ex:
            limitations.append(f"gcms_profile tool failed: {ex}")

        yield_pct = 0.0
        aroma = {"index": 0.8, "note": "default"}
        try:
            res = self.use_tool("yield_estimator", herb=herb, method=method,
                                 plant_water_ratio=parameters["plant_water_ratio"],
                                 duration_minutes=parameters["time_min"])
            yd = res.get("result", {})
            yield_pct = yd.get("estimated_yield_pct", 0.0)
            aroma = {
                "index": yd.get("aroma_preservation_index", 0.8),
                "note": "volatiles preserved" if yd.get("aroma_preservation_index", 0.8) > 0.7 else "thermal degradation risk",
                "method": method,
            }
        except Exception as ex:
            limitations.append(f"yield_estimator tool failed: {ex}")

        standardization = {
            "iso": "ISO 4720 (essential oil nomenclature)",
            "pharmacopoeia": "PhEur/USP identity + limits",
            "adulteration_checks": ["GC-MS chemotype match", "specific gravity", "refractive index"],
        }

        # Best/base/worst scenarios.
        scenarios = {
            "best": {"yield_pct": round(yield_pct * 1.25, 3), "aroma_index": round(min(1.0, aroma["index"] + 0.1), 3)},
            "base": {"yield_pct": round(yield_pct, 3), "aroma_index": round(aroma["index"], 3)},
            "worst": {"yield_pct": round(yield_pct * 0.7, 3), "aroma_index": round(max(0.0, aroma["index"] - 0.2), 3)},
        }

        output = {
            "herb": herb,
            "method": method,
            "parameters": parameters,
            "pretreatment": pretreatment,
            "gcms_profile": gcms,
            "yield_pct": round(yield_pct, 3),
            "aroma_preservation": aroma,
            "standardization": standardization,
            "scenarios": scenarios,
            "iteration": iteration,
        }
        degradation = 1 if any("inferred" in l for l in limitations) else 0
        return self._ok(output, degradation_level=degradation, limitations=limitations)


__all__ = ["CoreAnalysisAgent"]