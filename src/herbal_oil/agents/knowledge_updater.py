"""knowledge-updater agent (Step 4).

Queries the knowledge base for academic/professional evidence, surfaces 3-5
tiered citations, and flags coverage gaps for the crawl pipeline. Optionally
gap-fills with the knowledge_append tool (committing one synthetic-free
WebSearch-derived entry) only when a real URL is available.
"""
from __future__ import annotations

import re
from typing import Any

from ..core.base_agent import AgentResult, BaseAgent


class KnowledgeUpdaterAgent(BaseAgent):
    name = "knowledge-updater"
    persona = "research librarian for essential-oil extraction & aromatic chemistry"
    description = "Query SECOND-KNOWLEDGE-BRAIN.md for tiered citations; flag gaps for the crawl pipeline."
    tool_names = ("knowledge_query", "knowledge_append")
    output_schema = {
        "type": "object",
        "properties": {
            "citations": {"type": "array", "items": {"type": "string"}},
            "evidence": {"type": "array", "items": {"type": "object"}},
            "gaps": {"type": "array", "items": {"type": "string"}},
            "coverage": {"type": "string"},
        },
        "required": ["citations", "coverage"],
    }

    def solve(self, state: Any, **_: Any) -> AgentResult:
        analysis = state.step_outputs.get("core-analysis") or {}
        herb = analysis.get("herb", "essential oil") if isinstance(analysis, dict) else "essential oil"
        method = analysis.get("method", "") if isinstance(analysis, dict) else ""
        kws = [herb, method or "extraction", "GC-MS", "yield", "ISO 4720"]

        limitations: list[str] = []
        citations: list[str] = []
        evidence: list[dict[str, Any]] = []
        gaps: list[str] = []
        coverage = "Weak"

        try:
            res = self.use_tool("knowledge_query", keywords=kws, max_results=5)
            data = res.get("result", {})
            for c in data.get("citations", []):
                tier = c.get("tier", 3)
                citations.append(
                    f"[{c.get('authors','Unknown')} ({c.get('year','')})] {c.get('title','')}. "
                    f"{c.get('venue','')}. {c.get('doi','')}  Tier: {tier}"
                )
                evidence.append({
                    "source": c.get("source", "SECOND-KNOWLEDGE-BRAIN.md"),
                    "tier": tier,
                    "url": c.get("doi", ""),
                    "claim": c.get("title", ""),
                })
            coverage = data.get("coverage", "Weak")
            gaps = data.get("gaps", [])
        except Exception as ex:
            limitations.append(f"knowledge_query failed: {ex}")
            gaps.append(f"crawl query: {herb} {method} essential oil GC-MS")

        if coverage == "Weak" and not gaps:
            gaps.append(f"gap-fill: recent {herb} {method} yield/aroma study 2024+")

        out = {"citations": citations, "evidence": evidence, "gaps": gaps, "coverage": coverage}
        return self._ok(out, degradation_level=1 if coverage == "Weak" else 0, limitations=limitations)


__all__ = ["KnowledgeUpdaterAgent"]