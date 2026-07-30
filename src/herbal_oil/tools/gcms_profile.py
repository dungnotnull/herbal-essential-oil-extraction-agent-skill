"""GC-MS profile estimator.

Produces a plausible GC-MS chemotype composition for a given herb based on a
small embedded chemotype reference table (literature-typical ranges). The
tool is deterministic and side-effect free; it never invents compounds for
herbs outside the table, instead returning a generic terpene scaffold with a
`source: inferred` flag (degradation-friendly).
"""
from __future__ import annotations

from typing import Any

from ..core.base_tool import BaseTool

# Literature-typical chemotype composition (% of identified volatiles).
CHEMOTYPES: dict[str, list[tuple[str, float, float, str]]] = {
    "lavender": [("linalool", 25.0, 45.0, "monoterpene alcohol"),
                 ("linalyl acetate", 20.0, 40.0, "ester"),
                 ("lavandulyl acetate", 2.0, 6.0, "ester"),
                 ("caryophyllene", 2.0, 6.0, "sesquiterpene"),
                 ("terpinen-4-ol", 2.0, 5.0, "monoterpene alcohol")],
    "peppermint": [("menthol", 30.0, 50.0, "monoterpene alcohol"),
                   ("menthone", 10.0, 25.0, "monoterpene ketone"),
                   ("menthyl acetate", 3.0, 10.0, "ester"),
                   ("1,8-cineole", 5.0, 12.0, "oxide"),
                   ("menthofuran", 1.0, 5.0, "furan (oxidation marker)")],
    "clove": [("eugenol", 75.0, 90.0, "phenylpropanoid"),
              ("eugenyl acetate", 5.0, 15.0, "ester"),
              ("beta-caryophyllene", 2.0, 8.0, "sesquiterpene"),
              ("alpha-humulene", 0.5, 2.0, "sesquiterpene")],
    "lemongrass": [("geranial (citral a)", 30.0, 45.0, "monoterpene aldehyde"),
                   ("neral (citral b)", 20.0, 35.0, "monoterpene aldehyde"),
                   ("geraniol", 3.0, 10.0, "monoterpene alcohol"),
                   ("myrcene", 2.0, 8.0, "monoterpene")],
    "rosemary": [("1,8-cineole", 25.0, 45.0, "oxide"),
                 ("alpha-pinene", 10.0, 25.0, "monoterpene"),
                 ("camphor", 5.0, 20.0, "monoterpene ketone"),
                 ("verbenone", 1.0, 5.0, "monoterpene ketone")],
}

GENERIC_SCAFFOLD = [("linalool", 10.0, 30.0, "monoterpene alcohol"),
                    ("alpha-pinene", 5.0, 20.0, "monoterpene"),
                    ("beta-caryophyllene", 2.0, 10.0, "sesquiterpene"),
                    ("1,8-cineole", 2.0, 12.0, "oxide")]


class GCMSProfileTool(BaseTool):
    name = "gcms_profile"
    description = "Estimate a GC-MS chemotype composition for an herb from a literature-typical reference table; flags inferred profiles for unknown herbs."
    parameters = {
        "type": "object",
        "properties": {
            "herb": {"type": "string", "minLength": 2, "description": "Common or Latin herb name"},
            "volatility_budget": {"type": "number", "minimum": 0, "maximum": 100,
                                   "description": "Optional volatility-preserving fraction (%) used to scale thermolabile compounds."},
        },
        "required": ["herb"],
        "additionalProperties": False,
    }

    def run(self, herb: str, volatility_budget: float = 100.0, **_: Any) -> dict[str, Any]:
        key = herb.strip().lower()
        known = next((k for k in CHEMOTYPES if k in key or key in k), None)
        if known:
            comps = CHEMOTYPES[known]
            source = f"literature-typical ({known})"
            inferred = False
        else:
            comps = GENERIC_SCAFFOLD
            source = "inferred generic terpene scaffold"
            inferred = True
        # Take midpoint of each range; scale by volatility budget for thermolabile
        # markers (aldehydes, alcohols, oxides degrade with heat).
        scale = max(0.0, min(100.0, volatility_budget)) / 100.0
        thermolabile = {"monoterpene alcohol", "monoterpene aldehyde", "oxide", "ester", "furan (oxidation marker)"}
        composition = []
        for name, lo, hi, cls in comps:
            mid = (lo + hi) / 2.0
            factor = scale if cls in thermolabile else 1.0
            composition.append({
                "compound": name,
                "approx_pct": round(mid * factor, 2),
                "range_pct": [lo, hi],
                "class": cls,
                "thermolabile": cls in thermolabile,
            })
        composition.sort(key=lambda c: c["approx_pct"], reverse=True)
        return {
            "herb": herb,
            "chemotype": composition,
            "source": source,
            "inferred": inferred,
        }


__all__ = ["GCMSProfileTool", "CHEMOTYPES"]