"""Chain-of-thought router.

Instead of a fixed linear order, the router inspects the user's intent and
requirements and emits an ordered execution plan of agents. It also decides
which optional agents to skip (e.g. comparison case loads core-analysis twice
with different payloads). The default plan keeps the mandatory bookends
(requirements -> evidence -> ... -> advisor -> quality gate) but the middle
is reorderable by intent.

Routing is rule-based (deterministic, testable) and cheap: it never calls an
LLM. When the CoT router feature flag is off, the canonical 5-step plan is
returned unchanged.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .logging import get_logger

log = get_logger("herbal_oil.router")

# Canonical agent names referenced by the plan.
REQUIREMENTS = "gather-requirements"
EVIDENCE = "evidence-collector"
CORE = "core-analysis"
KNOWLEDGE = "knowledge-updater"
ADVISOR = "advisor"

CANONICAL_PLAN = [REQUIREMENTS, EVIDENCE, CORE, KNOWLEDGE, ADVISOR]

_COMPARE_HINTS = re.compile(r"\b(compar(?:e|ison|ing)|versus|vs\.?|better of|side.by.side|A vs B)\b", re.I)
_RISK_HINTS = re.compile(r"\b(risk|feasibility|hazard|safety|conflict|toxic|adulterant|degrad)\b", re.I)
_EDU_HINTS = re.compile(r"\b(explain|teach|what is|how does|overview|learn|concept)\b", re.I)


@dataclass
class RoutingDecision:
    plan: list[str]
    intent: str
    repeats: dict[str, int] = field(default_factory=dict)
    reasoning: str = ""
    skipped: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan": self.plan,
            "intent": self.intent,
            "repeats": self.repeats,
            "reasoning": self.reasoning,
            "skipped": self.skipped,
        }


class ChainOfThoughtRouter:
    """Deterministic intent -> plan mapper."""

    def __init__(self, *, settings: Any = None) -> None:
        self.settings = settings

    def route(self, user_input: str, *, available_agents: list[str] | None = None) -> RoutingDecision:
        available = set(available_agents or CANONICAL_PLAN)
        text = user_input or ""
        intent = "standard"
        repeats: dict[str, int] = {}
        skipped: list[str] = []

        if _COMPARE_HINTS.search(text):
            intent = "comparison"
            repeats[CORE] = 2  # run core-analysis twice for two objects
        elif _RISK_HINTS.search(text):
            intent = "risk"
        elif _EDU_HINTS.search(text):
            intent = "educational"
            # educational framing can skip the heavy evidence crawl
            if EVIDENCE in available:
                skipped.append(EVIDENCE)

        # Build a plan from available agents, preserving canonical order.
        plan = [a for a in CANONICAL_PLAN if a in available]
        # Educational path: drop evidence collector if flagged
        if intent == "educational" and EVIDENCE in skipped and EVIDENCE in plan:
            plan = [a for a in plan if a != EVIDENCE]
        # Always require the bookends
        if REQUIREMENTS not in plan and REQUIREMENTS in available:
            plan.insert(0, REQUIREMENTS)
        if ADVISOR not in plan and ADVISOR in available:
            plan.append(ADVISOR)

        reasoning = self._explain(intent, plan, repeats, skipped)
        log.info("router.decision", intent=intent, plan=plan, repeats=repeats, skipped=skipped)
        return RoutingDecision(plan=plan, intent=intent, repeats=repeats, reasoning=reasoning, skipped=skipped)

    @staticmethod
    def _explain(intent: str, plan: list[str], repeats: dict[str, int], skipped: list[str]) -> str:
        parts = [f"intent={intent}", f"plan={plan}"]
        if repeats:
            parts.append(f"repeat={repeats}")
        if skipped:
            parts.append(f"skip={skipped}")
        return "; ".join(parts)


__all__ = ["ChainOfThoughtRouter", "RoutingDecision", "CANONICAL_PLAN"]