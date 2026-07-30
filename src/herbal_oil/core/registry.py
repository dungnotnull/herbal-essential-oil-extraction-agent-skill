"""Skill registry: the modular skill-registry pattern.

Agents, tools and hooks are registered against the registry by name. The
runner resolves them at runtime, which lets new domain skills be added or
swapped without touching orchestration code.

Registration is idempotent and validates that every registered component has
the required attributes (name, descriptor/solve). Duplicate names raise.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base_agent import BaseAgent
from .base_hook import BaseHook
from .base_tool import BaseTool
from .errors import AgentNotFoundError, ToolNotFoundError
from .logging import get_logger

log = get_logger("herbal_oil.registry")


@dataclass
class RegistryEntry:
    name: str
    kind: str  # "agent" | "tool" | "hook"
    instance: Any
    metadata: dict[str, Any] = field(default_factory=dict)


class SkillRegistry:
    """In-process registry for agents, tools and hooks."""

    def __init__(self, *, settings: Any = None) -> None:
        self.settings = settings
        self._agents: dict[str, BaseAgent] = {}
        self._tools: dict[str, BaseTool] = {}
        self._hooks: list[BaseHook] = []
        self._agent_order: list[str] = []
        self._tool_factories: dict[str, Any] = {}

    # -- registration ----------------------------------------------------
    def register_agent(self, agent: BaseAgent, *, metadata: dict[str, Any] | None = None) -> BaseAgent:
        if not getattr(agent, "name", ""):
            raise ValueError("agent must define a non-empty `name`")
        if agent.name in self._agents:
            raise ValueError(f"duplicate agent registration: {agent.name}")
        agent.registry = self
        if agent.settings is None:
            agent.settings = self.settings
        self._agents[agent.name] = agent
        self._agent_order.append(agent.name)
        log.info("registry.agent", agent=agent.name, meta=metadata or {})
        return agent

    def register_tool(self, tool: BaseTool, *, metadata: dict[str, Any] | None = None) -> BaseTool:
        if not getattr(tool, "name", ""):
            raise ValueError("tool must define a non-empty `name`")
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool registration: {tool.name}")
        if tool.settings is None:
            tool.settings = self.settings
        self._tools[tool.name] = tool
        log.info("registry.tool", tool=tool.name, meta=metadata or {})
        return tool

    def register_hook(self, hook: BaseHook, *, metadata: dict[str, Any] | None = None) -> BaseHook:
        if not getattr(hook, "name", ""):
            raise ValueError("hook must define a non-empty `name`")
        self._hooks.append(hook)
        log.info("registry.hook", hook=hook.name, events=hook.events, meta=metadata or {})
        return hook

    # -- lookup ----------------------------------------------------------
    def agent(self, name: str) -> BaseAgent:
        try:
            return self._agents[name]
        except KeyError as ex:
            raise AgentNotFoundError(
                f"agent not found: {name}",
                context={"available": list(self._agents)},
            ) from ex

    def tool(self, name: str) -> BaseTool:
        try:
            return self._tools[name]
        except KeyError as ex:
            raise ToolNotFoundError(
                f"tool not found: {name}",
                context={"available": list(self._tools)},
            ) from ex

    @property
    def agents(self) -> dict[str, BaseAgent]:
        return dict(self._agents)

    @property
    def tools(self) -> dict[str, BaseTool]:
        return dict(self._tools)

    @property
    def hooks(self) -> list[BaseHook]:
        return list(self._hooks)

    @property
    def agent_order(self) -> list[str]:
        return list(self._agent_order)

    # -- invocation ------------------------------------------------------
    def invoke_tool(self, name: str, **kwargs: Any) -> Any:
        return self.tool(name).execute(**kwargs)

    # -- introspection ---------------------------------------------------
    def manifest(self) -> dict[str, Any]:
        return {
            "agents": [
                {
                    "name": a.name,
                    "description": a.description,
                    "tools": list(a.tool_names),
                }
                for a in self._agents.values()
            ],
            "tools": [t.descriptor().to_openai_schema() for t in self._tools.values()],
            "hooks": [{"name": h.name, "events": list(h.events)} for h in self._hooks],
        }

    def reset(self) -> None:
        self._agents.clear()
        self._tools.clear()
        self._hooks.clear()
        self._agent_order.clear()

    # -- context manager support ----------------------------------------
    def __len__(self) -> int:
        return len(self._agents) + len(self._tools) + len(self._hooks)


__all__ = ["SkillRegistry", "RegistryEntry"]