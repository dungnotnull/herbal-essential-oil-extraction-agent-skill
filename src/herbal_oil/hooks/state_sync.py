"""State synchronization hooks: keep the evidence ledger deduped and
periodically checkpoint state to disk so long runs survive interruption.
"""
from __future__ import annotations

from typing import Any

from ..core.base_hook import BaseHook, HookContext
from ..core.logging import get_logger

log = get_logger("herbal_oil.hook.state_sync")


class EvidenceLedgerHook(BaseHook):
    name = "evidence-ledger-hook"
    events = ("on_evidence_added",)

    def on_evidence_added(self, ctx: HookContext) -> None:
        item = ctx.payload.get("item")
        if isinstance(item, dict):
            # Ensure tier within range; coerce if needed.
            tier = item.get("tier", 4)
            if not (isinstance(tier, int) and 1 <= tier <= 4):
                item["tier"] = 4
        log.info("evidence.added", run_id=ctx.run_id, count=len(ctx.state.evidence))


class StateCheckpointHook(BaseHook):
    name = "state-checkpoint-hook"
    events = ("on_step_complete", "on_run_complete")

    def __init__(self, *, checkpoint_dir: str | None = None, every_n_steps: int = 2) -> None:
        self.checkpoint_dir = checkpoint_dir
        self.every_n_steps = every_n_steps
        self._completed = 0

    def _dir(self, ctx: HookContext) -> str:
        if self.checkpoint_dir:
            return self.checkpoint_dir
        root = getattr(ctx.state, "_root", None)
        import os
        return os.path.join(os.getcwd(), "logs", "checkpoints")

    def on_step_complete(self, ctx: HookContext) -> None:
        self._completed += 1
        if self._completed % self.every_n_steps != 0:
            return
        self._checkpoint(ctx)

    def on_run_complete(self, ctx: HookContext) -> None:
        self._checkpoint(ctx)

    def _checkpoint(self, ctx: HookContext) -> None:
        import os
        from pathlib import Path

        d = Path(self._dir(ctx))
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"state-{ctx.run_id}.json"
        try:
            ctx.state.checkpoint(path)
            log.info("checkpoint.written", run_id=ctx.run_id, path=str(path))
        except Exception as ex:
            log.warning("checkpoint.error", run_id=ctx.run_id, error=str(ex))


__all__ = ["EvidenceLedgerHook", "StateCheckpointHook"]