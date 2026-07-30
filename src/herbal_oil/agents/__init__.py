"""Domain agents for the herbal-oil skill.

Each agent extends ``herbal_oil.core.base_agent.BaseAgent`` and implements a
deterministic ``solve`` path grounded in the knowledge base and the registered
tools. When an LLM client is bound, the same agent can prompt the model for a
richer narrative; the rule-based path guarantees the pipeline always runs.
"""
from .gather_requirements import GatherRequirementsAgent
from .evidence_collector import EvidenceCollectorAgent
from .core_analysis import CoreAnalysisAgent
from .knowledge_updater import KnowledgeUpdaterAgent
from .advisor import AdvisorAgent

ALL_AGENTS = [
    GatherRequirementsAgent,
    EvidenceCollectorAgent,
    CoreAnalysisAgent,
    KnowledgeUpdaterAgent,
    AdvisorAgent,
]

__all__ = [
    "GatherRequirementsAgent",
    "EvidenceCollectorAgent",
    "CoreAnalysisAgent",
    "KnowledgeUpdaterAgent",
    "AdvisorAgent",
    "ALL_AGENTS",
]