"""Lifecycle hooks: structured logging and per-step timing."""
from __future__ import annotations

from typing import Any

from ..core.base_hook import BaseHook, HookContext
from ..core.logging import get_logger

log = get_logger("herbal_oil.hook.lifecycle")


class LoggingHook(BaseHook):
    name = "logging-hook"
    events = ("on_run_start", "on_step_start", "on_step_complete", "on_step_error", "on_gate", "on_degradation", "on_run_complete")

    def on_run_start(self, ctx: HookContext) -> None:
        log.info("lifecycle.run.start", run_id=ctx.run_id, language=ctx.state.language)

    def on_step_start(self, ctx: HookContext) -> None:
        log.info("lifecycle.step.start", run_id=ctx.run_id, step=ctx.payload.get("step"))

    def on_step_complete(self, ctx: HookContext) -> None:
        log.info("lifecycle.step.complete", run_id=ctx.run_id, step=ctx.payload.get("step"))

    def on_step_error(self, ctx: HookContext) -> None:
        log.error("lifecycle.step.error", run_id=ctx.run_id, step=ctx.payload.get("step"), error=ctx.payload.get("error"))

    def on_gate(self, ctx: HookContext) -> None:
        log.info("lifecycle.gate", run_id=ctx.run_id, gate=ctx.payload.get("gate"), passed=ctx.payload.get("passed"))

    def on_degradation(self, ctx: HookContext) -> None:
        log.warning("lifecycle.degradation", run_id=ctx.run_id, degradation_level=ctx.payload.get("degradation_level"), reason=ctx.payload.get("reason"))

    def on_run_complete(self, ctx: HookContext) -> None:
        log.info("lifecycle.run.complete", run_id=ctx.run_id, degradation=ctx.state.degradation_level)


class TimingHook(BaseHook):
    name = "timing-hook"
    events = ("on_step_start", "on_step_complete")

    def __init__(self) -> None:
        self._starts: dict[str, float] = {}
        self.durations: dict[str, float] = {}

    def on_step_start(self, ctx: HookContext) -> None:
        import time

        step = ctx.payload.get("step", "")
        self._starts[step] = time.perf_counter()

    def on_step_complete(self, ctx: HookContext) -> None:
        import time

        step = ctx.payload.get("step", "")
        if step in self._starts:
            self.durations[step] = (time.perf_counter() - self._starts.pop(step)) * 1000.0
            ctx.state.metadata.setdefault("timings_ms", {})[step] = round(self.durations[step], 2)


__all__ = ["LoggingHook", "TimingHook"]