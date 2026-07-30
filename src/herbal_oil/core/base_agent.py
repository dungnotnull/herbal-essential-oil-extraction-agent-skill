"""Base agent primitive. Agents own a persona, a toolset, and an input/output
schema, and produce a deterministic ``AgentResult``.

The runtime is LLM-agnostic: a real deployment plugs an LLM client into
``llm_call``. When no client is configured, agents fall back to a rule-based
solver derived from the knowledge base and tool outputs so the pipeline still
runs end-to-end (degradation Level 2-3) - this is the production-grade
graceful-fallback behaviour required by the spec.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .context import ContextManager
from .errors import LLMCallError
from .logging import get_logger
from .schemas import validate

log = get_logger("herbal_oil.agent")


@dataclass
class AgentResult:
    agent: str
    ok: bool
    output: Any = None
    degradation_level: int = 0
    limitations: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "ok": self.ok,
            "output": self.output,
            "degradation_level": self.degradation_level,
            "limitations": self.limitations,
            "error": self.error,
        }


class BaseAgent:
    name: str = "base"
    persona: str = ""
    description: str = ""
    output_schema: dict[str, Any] = {}
    tool_names: tuple[str, ...] = ()

    def __init__(self, *, registry: Any = None, settings: Any = None, llm_client: Any = None) -> None:
        self.registry = registry
        self.settings = settings
        self.llm_client = llm_client
        self.context = ContextManager(
            budget_tokens=getattr(settings, "pipeline", None).context_token_budget
            if settings is not None and getattr(settings, "pipeline", None) is not None
            else 180_000,
            reserve_tokens=getattr(settings, "pipeline", None).context_reserve_tokens
            if settings is not None and getattr(settings, "pipeline", None) is not None
            else 8_000,
        )

    # -- tool access -----------------------------------------------------
    def use_tool(self, name: str, **kwargs: Any) -> Any:
        if self.registry is None:
            raise LLMCallError(f"no registry bound to agent {self.name}", model="n/a")
        return self.registry.invoke_tool(name, **kwargs)

    # -- LLM call with graceful fallback ---------------------------------
    def llm_call(self, prompt: str, *, system: str | None = None) -> str:
        """Call the bound LLM client. Falls back to ``fallback_model`` on error.

        If no client is bound, returns an empty string (agents must then rely
        on their rule-based ``solve`` path); this is logged as degradation.
        """
        if self.llm_client is None:
            log.warning("llm.no_client", agent=self.name)
            return ""
        llm_cfg = getattr(self.settings, "llm", None) if self.settings is not None else None
        model = getattr(llm_cfg, "model", "claude")
        fallback = getattr(llm_cfg, "fallback_model", "claude-haiku")
        for attempt, mdl in enumerate((model, fallback)):
            try:
                return self.llm_client.complete(prompt, model=mdl, system=system)
            except Exception as ex:
                log.error("llm.call.error", agent=self.name, model=mdl, attempt=attempt, error=str(ex))
                if attempt == 0:
                    continue
                raise LLMCallError(
                    f"LLM call failed for {self.name}: {ex}",
                    provider=getattr(llm_cfg, "provider", ""),
                    model=mdl,
                ) from ex
        return ""

    # -- the contract every agent implements -----------------------------
    def solve(self, state: Any) -> AgentResult:
        """Compute this agent's output from pipeline state.

        Subclasses implement this. The default raises to force override.
        """
        raise NotImplementedError(f"{type(self).__name__}.solve not implemented")

    def _validate_output(self, output: Any) -> None:
        if self.output_schema:
            validate(output, self.output_schema, label=f"agent:{self.name}.output")

    def _ok(self, output: Any, *, degradation_level: int = 0, limitations: list[str] | None = None) -> AgentResult:
        self._validate_output(output)
        return AgentResult(
            agent=self.name,
            ok=True,
            output=output,
            degradation_level=degradation_level,
            limitations=limitations or [],
        )

    def _fail(self, error: str, *, degradation_level: int = 1, output: Any = None) -> AgentResult:
        return AgentResult(
            agent=self.name,
            ok=False,
            output=output,
            degradation_level=degradation_level,
            error=error,
        )


__all__ = ["BaseAgent", "AgentResult"]