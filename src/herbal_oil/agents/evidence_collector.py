"""evidence-collector agent (Step 2).

Builds an evidence bundle: queries the knowledge base (Tier-1/2 anchor) and,
when web tools are enabled, augments with live web results. Each item is
tagged with a source + tier + access date. On failure it falls back to the
knowledge base only and flags the limitation (degradation Level 1-2).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..core.base_agent import AgentResult, BaseAgent
from ..core.state import EvidenceItem


class EvidenceCollectorAgent(BaseAgent):
    name = "evidence-collector"
    persona = "essential-oil extraction & aromatic-chemistry data librarian"
    description = "Fetch authoritative real-time and reference data; tag every item with source + tier + access date."
    tool_names = ("web_search", "web_fetch", "knowledge_query")
    output_schema = {
        "type": "object",
        "properties": {
            "current_data": {"type": "array", "items": {"type": "object"}},
            "authoritative_docs": {"type": "array", "items": {"type": "object"}},
            "recent_news": {"type": "array", "items": {"type": "object"}},
            "reference_benchmarks": {"type": "array", "items": {"type": "object"}},
            "evidence": {"type": "array", "items": {"type": "object"}},
            "coverage": {"type": "string"},
            "degradation": {"type": "string"},
        },
        "required": ["evidence", "coverage"],
    }

    def solve(self, state: Any, **_: Any) -> AgentResult:
        req = state.requirements or {}
        obj = req.get("object", "essential oil extraction")
        kws = [w for w in obj.replace("essential-oil", "essential oil").split() if len(w) > 2][:5]
        if not kws:
            kws = ["essential oil", "extraction", "GC-MS"]

        evidence: list[dict[str, Any]] = []
        limitations: list[str] = []
        degradation = 0

        # Anchor: knowledge base.
        try:
            kb = self.use_tool("knowledge_query", keywords=kws, max_results=5)
            for c in kb.get("result", {}).get("citations", []):
                evidence.append({
                    "source": c.get("source", "SECOND-KNOWLEDGE-BRAIN.md"),
                    "tier": c.get("tier", 3),
                    "url": c.get("doi", ""),
                    "accessed_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "claim": c.get("title", ""),
                    "extra": {k: c.get(k) for k in ("authors", "year", "venue") if c.get(k)},
                })
        except Exception as ex:
            degradation = max(degradation, 2)
            limitations.append(f"knowledge query failed: {ex}; using degraded bundle")

        # Live web augmentation (optional).
        features = getattr(self.settings, "features", None)
        web_enabled = getattr(features, "enable_web_tools", True) if features else True
        recent_news: list[dict[str, Any]] = []
        if web_enabled:
            try:
                search = self.use_tool("web_search", query=" ".join(kws + ["extraction yield GC-MS"]), max_results=3)
                for r in search.get("result", []):
                    recent_news.append({
                        "source": "web",
                        "tier": 4,
                        "url": r.get("url", ""),
                        "accessed_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        "claim": r.get("title", ""),
                    })
            except Exception as ex:
                degradation = max(degradation, 1)
                limitations.append(f"web search failed: {ex}")

        coverage = "Strong" if len(evidence) >= 3 else "Moderate" if evidence else "Weak"
        # Authoritative docs are knowledge-base tier-1/2 entries.
        auth_docs = [e for e in evidence if e.get("tier", 4) <= 2]
        reference_benchmarks = evidence[:3]

        bundle = {
            "current_data": recent_news or evidence[:2],
            "authoritative_docs": auth_docs,
            "recent_news": recent_news,
            "reference_benchmarks": reference_benchmarks,
            "evidence": evidence + recent_news,
            "coverage": coverage,
            "degradation": f"Level {degradation}" if degradation else "none",
        }
        return self._ok(bundle, degradation_level=degradation, limitations=limitations)


__all__ = ["EvidenceCollectorAgent"]