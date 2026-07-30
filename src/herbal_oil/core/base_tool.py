"""Base tool primitive with a declarative JSON-schema descriptor.

Tools are the only way agents interact with the outside world (web, knowledge
base, computation). Each tool exposes an OpenAI-style function schema and an
``execute`` handler. The registry resolves tools by name at runtime.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .errors import ToolExecutionError
from .logging import get_logger

log = get_logger("herbal_oil.tool")


@dataclass
class ToolDescriptor:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON-schema describing accepted arguments
    returns: dict[str, Any] = field(default_factory=dict)

    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class BaseTool:
    """Subclass and implement ``run``. ``name``/``description``/``parameters``
    must be set as class attributes or returned by ``descriptor()``."""

    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {}
    returns: dict[str, Any] = {}
    requires_network: bool = False

    def __init__(self, *, settings: Any = None) -> None:
        self.settings = settings

    # -- schema ----------------------------------------------------------
    def descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
            returns=self.returns,
        )

    # -- execution -------------------------------------------------------
    def run(self, **kwargs: Any) -> Any:
        raise NotImplementedError(f"{type(self).__name__}.run not implemented")

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Validate args, run, and wrap the result in a structured envelope."""
        from .schemas import validate

        start = time.perf_counter()
        args_desc = {k: v for k, v in kwargs.items() if k in self.parameters.get("properties", {})}
        # Validate arguments against the declared schema (best-effort: extra
        # args are allowed so callers can pass context metadata).
        try:
            validate(args_desc, self.parameters, label=f"tool:{self.name}.args")
        except Exception as ex:  # validation -> ToolExecutionError
            log.warning("tool.args.invalid", tool=self.name, error=str(ex))
            raise ToolExecutionError(
                f"{self.name}: invalid arguments: {ex}",
                context={"tool": self.name},
            ) from ex

        try:
            result = self.run(**kwargs)
            elapsed = (time.perf_counter() - start) * 1000.0
            log.info("tool.ok", tool=self.name, ms=round(elapsed, 2))
            return {
                "tool": self.name,
                "ok": True,
                "result": result,
                "elapsed_ms": round(elapsed, 2),
            }
        except ToolExecutionError:
            raise
        except Exception as ex:
            elapsed = (time.perf_counter() - start) * 1000.0
            log.error("tool.error", tool=self.name, error=str(ex))
            raise ToolExecutionError(
                f"{self.name}: {ex}", context={"tool": self.name}
            ) from ex


class ToolError(Exception):
    """Legacy alias kept for external import compatibility."""


__all__ = ["BaseTool", "ToolDescriptor", "ToolError"]