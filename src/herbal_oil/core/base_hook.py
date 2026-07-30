"""Base hook primitive for lifecycle management, state sync and event emission.

Hooks are callbacks fired at well-defined lifecycle points. They are pure
side-effect channels: they must not mutate the agent result directly, only
observe / augment shared state via the HookContext. A hook can veto a step by
raising, but the runner will treat that as a step failure (with degradation).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .logging import get_logger
from .state import PipelineState

log = get_logger("herbal_oil.hook")

# Canonical lifecycle events. Plugins may register for any subset.
LIFECYCLE_EVENTS = (
    "on_run_start",
    "on_step_start",
    "on_step_complete",
    "on_step_error",
    "on_evidence_added",
    "on_gate",
    "on_degradation",
    "on_run_complete",
)


@dataclass
class HookContext:
    run_id: str
    state: PipelineState
    event: str
    payload: dict[str, Any] = field(default_factory=dict)


class BaseHook:
    """Subclass and override the relevant lifecycle handlers."""

    name: str = "base_hook"
    events: tuple[str, ...] = ("on_run_complete",)

    def matches(self, event: str) -> bool:
        return event in self.events

    # -- lifecycle handlers (override as needed) -------------------------
    def on_run_start(self, ctx: HookContext) -> None:  # noqa: D401
        """Called once at pipeline start."""

    def on_step_start(self, ctx: HookContext) -> None:
        pass

    def on_step_complete(self, ctx: HookContext) -> None:
        pass

    def on_step_error(self, ctx: HookContext) -> None:
        pass

    def on_evidence_added(self, ctx: HookContext) -> None:
        pass

    def on_gate(self, ctx: HookContext) -> None:
        pass

    def on_degradation(self, ctx: HookContext) -> None:
        pass

    def on_run_complete(self, ctx: HookContext) -> None:
        pass

    # -- dispatch --------------------------------------------------------
    def dispatch(self, event: str, ctx: HookContext) -> None:
        handler = getattr(self, event, None)
        if handler is None:
            return
        try:
            handler(ctx)
        except Exception as ex:  # hooks must never crash the pipeline
            log.warning("hook.error", hook=self.name, hook_event=event, error=str(ex))


__all__ = ["BaseHook", "HookContext", "LIFECYCLE_EVENTS"]