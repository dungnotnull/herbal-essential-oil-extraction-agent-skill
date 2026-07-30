"""Factory: assemble a fully-wired SkillRegistry from settings.

This is the single entry point used by scripts and the CLI. It instantiates
all agents, tools and hooks, binds the LLM client (if provided), and returns a
ready-to-run PipelineRunner. Keeping wiring in one place makes the skill
declarative and testable.
"""
from __future__ import annotations

from typing import Any

from .agents import ALL_AGENTS
from .core import ChainOfThoughtRouter, PipelineRunner, SkillRegistry
from .hooks import ALL_HOOKS
from .tools import ALL_TOOLS


def build_registry(settings: Any = None, *, llm_client: Any = None) -> SkillRegistry:
    registry = SkillRegistry(settings=settings)
    for tool_cls in ALL_TOOLS:
        registry.register_tool(tool_cls(settings=settings))
    for agent_cls in ALL_AGENTS:
        registry.register_agent(agent_cls(settings=settings, llm_client=llm_client))
    for hook_cls in ALL_HOOKS:
        registry.register_hook(hook_cls())
    return registry


def build_runner(settings: Any = None, *, llm_client: Any = None) -> PipelineRunner:
    registry = build_registry(settings, llm_client=llm_client)
    router = ChainOfThoughtRouter(settings=settings)
    return PipelineRunner(registry, settings=settings, router=router)


__all__ = ["build_registry", "build_runner"]