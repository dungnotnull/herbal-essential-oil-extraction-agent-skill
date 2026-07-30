"""advisor agent (Step 5).

Synthesizes the prior steps into a risk-disclosed conclusion. Picks exactly
one verdict from the declared set, builds best/base/worst scenarios, lists
>=3 key risks, the evidence chain, remediation, and prepends the mandatory
disclosure before the conclusion.
"""
from __future__ import annotations

from typing import Any

from ..core.base_agent import AgentResult, BaseAgent

VERDICTS = ["Optimal Extraction", "Conditional (thermal)", "Yield/Aroma Loss", "Inconclusive"]


class AdvisorAgent(BaseAgent):
    name = "advisor"
    persona = "senior essential-oil extraction & aromatic-chemistry advisor"
    description = "Synthesize all prior analysis into a risk-disclosed conclusion with a full evidence chain and recommended actions."
    tool_names = ("knowledge_query",)
    output_schema = {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": VERDICTS},
            "summary": {"type": "string"},
            "disclosure": {"type": "string"},
            "scenarios": {"type": "object"},
            "key_risks": {"type": "array", "items": {"type": "string"}, "minItems": 3},
            "evidence_chain": {"type": "array", "items": {"type": "string"}},
            "remediation": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["verdict", "disclosure", "key_risks"],
    }

    def solve(self, state: Any, **_: Any) -> AgentResult:
        analysis = state.step_outputs.get("core-analysis") or {}
        evidence = state.step_outputs.get("evidence-collector") or {}
        knowledge = state.step_outputs.get("knowledge-updater") or {}

        method = analysis.get("method", "steam") if isinstance(analysis, dict) else "steam"
        aroma = analysis.get("aroma_preservation", {}) if isinstance(analysis, dict) else {}
        aroma_index = aroma.get("index", 0.8) if isinstance(aroma, dict) else 0.8
        yield_pct = analysis.get("yield_pct", 0.0) if isinstance(analysis, dict) else 0.0
        scenarios = analysis.get("scenarios", {}) if isinstance(analysis, dict) else {}

        # Verdict logic.
        if state.degradation_level >= 3 and not evidence:
            verdict = "Inconclusive"
        elif method == "sfe_co2" and aroma_index > 0.85:
            verdict = "Optimal Extraction"
        elif method in ("steam", "microwave") and aroma_index < 0.6:
            verdict = "Yield/Aroma Loss"
        elif method in ("steam", "hydro") and 0.6 <= aroma_index <= 0.85:
            verdict = "Conditional (thermal)"
        else:
            verdict = "Optimal Extraction" if aroma_index > 0.7 else "Conditional (thermal)"

        summary = (
            f"For {analysis.get('herb','the herb')} the recommended method is {method} "
            f"(yield ~{yield_pct}% w/w, aroma index {aroma_index}). "
            f"Verdict: {verdict}."
        )

        disclosure = (
            "DISCLOSURE: This analysis synthesizes literature-typical baselines and the "
            "current knowledge base. Actual yields and chemotypes vary with chemotype, "
            "harvest time, pretreatment and equipment; validate with on-site GC-MS before "
            "scale-up. Do not ingest oils neat; observe ISO 4720 and pharmacopoeia limits."
        )

        key_risks = [
            f"Thermal degradation of thermolabile volatiles (aroma index {aroma_index}) under {method}.",
            "Chemotype variability between batches invalidates a fixed parameter set.",
            "Oxidation/polymerization post-extraction if storage is not inert & cool.",
            f"Knowledge-base coverage is {knowledge.get('coverage','Moderate') if isinstance(knowledge, dict) else 'Moderate'}; recent literature may be missing.",
        ]

        evidence_chain = []
        for e in state.evidence[:6]:
            evidence_chain.append(
                f"claim '{e.claim[:60]}' <- [{e.source}] Tier {e.tier}"
                + (f" ({e.url})" if e.url else "")
            )

        remediation = [
            "Run a pilot batch and measure GC-MS to confirm chemotype before locking parameters.",
            "For thermolabile herbs, prefer SFE-CO2 or reduce steam residence time.",
            "Store oil under nitrogen at <15C in amber glass; log batch fingerprint.",
            "Queue the flagged knowledge gaps to the weekly crawl pipeline.",
        ]

        out = {
            "verdict": verdict,
            "summary": summary,
            "disclosure": disclosure,
            "scenarios": scenarios or {"best": {}, "base": {}, "worst": {}},
            "key_risks": key_risks[:3] + (key_risks[3:] if len(key_risks) > 3 else ["Batch-to-batch chemotype drift."]),
            "evidence_chain": evidence_chain,
            "remediation": remediation,
        }
        return self._ok(out, degradation_level=0)


__all__ = ["AdvisorAgent", "VERDICTS"]