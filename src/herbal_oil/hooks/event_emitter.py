"""Event emitter hook: forwards lifecycle events to an in-memory bus so
external integrations (UI, metrics) can subscribe without coupling to the
runner.
"""
from __future__ import annotations

from typing import Any, Callable

from ..core.base_hook import BaseHook, HookContext
from ..core.logging import get_logger

log = get_logger("herbal_oil.hook.event_emitter")


class EventEmitterHook(BaseHook):
    name = "event-emitter-hook"
    events = ("on_run_start", "on_step_start", "on_step_complete", "on_step_error", "on_evidence_added", "on_gate", "on_degradation", "on_run_complete")

    def __init__(self) -> None:
        self._subscribers: list[Callable[[str, dict[str, Any]], None]] = []
        self.events_log: list[dict[str, Any]] = []

    def subscribe(self, callback: Callable[[str, dict[str, Any]], None]) -> None:
        self._subscribers.append(callback)

    def _dispatch_all(self, event: str, ctx: HookContext) -> None:
        record = {"run_id": ctx.run_id, "event": event, "payload": ctx.payload}
        self.events_log.append(record)
        for cb in self._subscribers:
            try:
                cb(event, record)
            except Exception as ex:
                log.warning("subscriber.error", event=event, error=str(ex))

    def on_run_start(self, ctx: HookContext) -> None:
        self._dispatch_all("on_run_start", ctx)

    def on_step_start(self, ctx: HookContext) -> None:
        self._dispatch_all("on_step_start", ctx)

    def on_step_complete(self, ctx: HookContext) -> None:
        self._dispatch_all("on_step_complete", ctx)

    def on_step_error(self, ctx: HookContext) -> None:
        self._dispatch_all("on_step_error", ctx)

    def on_evidence_added(self, ctx: HookContext) -> None:
        self._dispatch_all("on_evidence_added", ctx)

    def on_gate(self, ctx: HookContext) -> None:
        self._dispatch_all("on_gate", ctx)

    def on_degradation(self, ctx: HookContext) -> None:
        self._dispatch_all("on_degradation", ctx)

    def on_run_complete(self, ctx: HookContext) -> None:
        self._dispatch_all("on_run_complete", ctx)


__all__ = ["EventEmitterHook"]