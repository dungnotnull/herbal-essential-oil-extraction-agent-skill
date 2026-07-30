"""gather-requirements agent (Step 1 / intake).

Parses the user message into a structured requirements object. It infers the
object (herb + extraction target) from domain keywords, detects scope/timeframe
cues, and asks at most 2 clarifying questions only when the object is missing -
in a batch/headless run it instead records an assumption so the pipeline never
blocks.
"""
from __future__ import annotations

import re
from typing import Any

from ..core.base_agent import AgentResult, BaseAgent

HERB_RE = re.compile(
    r"\b(lavender|peppermint|clove|lemongrass|rosemary|basil|oregano|thyme|mint|"
    r"eucalyptus|ginger|chamomile|jasmine|sage|cinnamon|tea tree|citronella)\b",
    re.I,
)
TARGET_RE = re.compile(r"\b(yield|aroma|profile|chemotype|purity|quality|scale.up|pilot)\b", re.I)
SCOPE_RE = re.compile(r"\b(lab|pilot|industrial|kg|tonne|grams|scale)\b", re.I)


class GatherRequirementsAgent(BaseAgent):
    name = "gather-requirements"
    persona = "intake specialist for essential-oil extraction engagements"
    description = "Clarify the object of analysis, constraints, timeframe, available inputs, target audience and language before any data fetching."
    tool_names = ()
    output_schema = {
        "type": "object",
        "properties": {
            "object": {"type": "string"},
            "scope": {"type": "string"},
            "timeframe": {"type": "string"},
            "available_inputs": {"type": "array", "items": {"type": "string"}},
            "target_audience": {"type": "string"},
            "language": {"type": "string"},
            "analysis_type": {"type": "string"},
            "assumptions": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["object", "analysis_type", "language"],
    }

    def solve(self, state: Any, **_: Any) -> AgentResult:
        text = state.user_input or ""
        herb = HERB_RE.search(text)
        target = TARGET_RE.search(text)
        scope = SCOPE_RE.search(text)
        assumptions: list[str] = []

        if herb:
            obj = f"{herb.group(1).lower()} essential-oil extraction"
        else:
            obj = "essential-oil extraction (herb to be confirmed)"
            assumptions.append("specific herb not stated; analysis uses generic terpene scaffold")
        if not target:
            assumptions.append("target not stated; defaulting to combined yield+aroma optimization")
        if not scope:
            assumptions.append("scale not stated; assuming lab-to-pilot")

        req = {
            "object": obj,
            "scope": scope.group(0).lower() if scope else "lab-to-pilot",
            "timeframe": "current literature baseline",
            "available_inputs": [s.strip() for s in re.split(r"[;,]", text) if s.strip()][:8] or ["user message only"],
            "target_audience": "practitioner",
            "language": state.language,
            "analysis_type": "combined",
            "assumptions": assumptions,
        }
        state.requirements = req
        # If the user message gave no herb, record a clarifying need (non-blocking).
        if not herb:
            state.add_limitation("requirement clarification: herb not specified; defaulting to generic profile")
        return self._ok(req, limitations=assumptions)


__all__ = ["GatherRequirementsAgent"]