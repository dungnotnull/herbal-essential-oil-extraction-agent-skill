"""Context-window management for the pipeline.

Token accounting is approximate (chars/4 heuristic) which is good enough for
budget enforcement without a tokenizer dependency. When the budget is
exceeded, the manager drops the oldest non-essential attachments and rolls up
prior step outputs into compact summaries so the next agent still has room.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .errors import ContextBudgetExceeded


def estimate_tokens(text: Any) -> int:
    """Rough token estimate: 1 token ~= 4 characters for English/mixed text."""
    if text is None:
        return 0
    if isinstance(text, (dict, list)):
        import json

        text = json.dumps(text, ensure_ascii=False)
    return max(1, len(str(text)) // 4)


@dataclass
class ContextFrame:
    role: str
    content: Any
    tokens: int
    essential: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"role": self.role, "content": self.content, "tokens": self.tokens, "essential": self.essential}


class ContextManager:
    """Maintains a bounded list of context frames for an agent run.

    Strategy when over budget:
      1. Drop non-essential frames (oldest first).
      2. Compact essential frames into a short summary.
      3. If still over, raise ContextBudgetExceeded.
    """

    def __init__(self, budget_tokens: int = 180_000, reserve_tokens: int = 8_000) -> None:
        if budget_tokens <= reserve_tokens:
            raise ValueError("budget_tokens must exceed reserve_tokens")
        self.budget = budget_tokens
        self.reserve = reserve_tokens
        self.usable = budget_tokens - reserve_tokens
        self.frames: list[ContextFrame] = []

    def add(self, role: str, content: Any, *, essential: bool = True) -> ContextFrame:
        frame = ContextFrame(role=role, content=content, tokens=estimate_tokens(content), essential=essential)
        self.frames.append(frame)
        return frame

    def total_tokens(self) -> int:
        return sum(f.tokens for f in self.frames)

    def over_budget(self) -> bool:
        return self.total_tokens() > self.usable

    def _drop_nonessential(self) -> int:
        before = self.total_tokens()
        self.frames = [f for f in self.frames if f.essential]
        return before - self.total_tokens()

    def _compact_oldest(self, keep_last: int = 2) -> None:
        if len(self.frames) <= keep_last:
            return
        head = self.frames[:-keep_last]
        tail = self.frames[-keep_last:]
        summary_tokens = sum(f.tokens for f in head)
        rolled = " | ".join(f"{f.role}: {str(f.content)[:120]}" for f in head)
        compact = ContextFrame(
            role="summary",
            content=f"[compacted {len(head)} frames] " + rolled,
            tokens=max(1, estimate_tokens(rolled)),
            essential=True,
        )
        self.frames = [compact] + tail

    def enforce(self) -> int:
        """Compact the context until it fits within the usable budget.

        Returns the final token count. Raises ContextBudgetExceeded if it
        cannot fit after compaction.
        """
        if not self.over_budget():
            return self.total_tokens()
        self._drop_nonessential()
        for keep in (2, 1, 0):
            self._compact_oldest(keep_last=keep)
            if not self.over_budget():
                return self.total_tokens()
        raise ContextBudgetExceeded(
            f"context still {self.total_tokens()} tokens after compaction (budget {self.usable})",
            context={"tokens": self.total_tokens(), "budget": self.usable},
        )

    def render(self) -> list[dict[str, Any]]:
        self.enforce()
        return [f.to_dict() for f in self.frames]

    def reset(self) -> None:
        self.frames.clear()


__all__ = ["ContextManager", "ContextFrame", "estimate_tokens"]