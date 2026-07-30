"""Domain error hierarchy with graceful-fallback semantics.

Every recoverable failure carries a `level` (degradation level 0-4) and a
`recoverable` flag so the runner can decide whether to retry, fall back, or
emit a limitation banner instead of crashing.
"""
from __future__ import annotations

from typing import Any


class HerbalOilError(Exception):
    """Base class for all herbal-oil runtime errors."""

    code: str = "HERBAL_OIL_ERROR"
    recoverable: bool = True
    degradation_level: int = 0

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "recoverable": self.recoverable,
            "degradation_level": self.degradation_level,
            "context": self.context,
        }


class ConfigError(HerbalOilError):
    code = "CONFIG_ERROR"
    recoverable = False


class SchemaValidationError(HerbalOilError):
    code = "SCHEMA_VALIDATION_ERROR"
    recoverable = True
    degradation_level = 0

    def __init__(self, message: str, *, errors: list[str] | None = None, context: dict[str, Any] | None = None) -> None:
        super().__init__(message, context=context)
        self.errors = errors or []

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["errors"] = self.errors
        return data


class ToolExecutionError(HerbalOilError):
    code = "TOOL_EXECUTION_ERROR"
    recoverable = True
    degradation_level = 1


class ToolNotFoundError(HerbalOilError):
    code = "TOOL_NOT_FOUND"
    recoverable = False


class AgentNotFoundError(HerbalOilError):
    code = "AGENT_NOT_FOUND"
    recoverable = False


class GateFailureError(HerbalOilError):
    """A quality gate failed and could not be auto-fixed within the retry budget."""

    code = "GATE_FAILURE"
    recoverable = False
    degradation_level = 2

    def __init__(self, message: str, *, gate: str, attempts: int, context: dict[str, Any] | None = None) -> None:
        super().__init__(message, context=context)
        self.gate = gate
        self.attempts = attempts

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["gate"] = self.gate
        data["attempts"] = self.attempts
        return data


class DegradationError(HerbalOilError):
    """Raised when degradation reaches level 4 (no data available anywhere)."""

    code = "DEGRADATION_LEVEL_4"
    recoverable = False
    degradation_level = 4


class LLMCallError(HerbalOilError):
    """An LLM call failed; the runner should attempt the fallback model."""

    code = "LLM_CALL_ERROR"
    recoverable = True
    degradation_level = 1

    def __init__(self, message: str, *, provider: str = "", model: str = "", context: dict[str, Any] | None = None) -> None:
        super().__init__(message, context=context)
        self.provider = provider
        self.model = model

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["provider"] = self.provider
        data["model"] = self.model
        return data


class ContextBudgetExceeded(HerbalOilError):
    code = "CONTEXT_BUDGET_EXCEEDED"
    recoverable = True
    degradation_level = 2


__all__ = [
    "HerbalOilError",
    "ConfigError",
    "SchemaValidationError",
    "ToolExecutionError",
    "ToolNotFoundError",
    "AgentNotFoundError",
    "GateFailureError",
    "DegradationError",
    "LLMCallError",
    "ContextBudgetExceeded",
]