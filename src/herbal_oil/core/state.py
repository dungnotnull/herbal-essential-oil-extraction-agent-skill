"""Pipeline state container shared across agents, tools and hooks.

State is the single source of truth for a run: it carries the user input,
the structured output of each step, the degradation level, the evidence
ledger, and the quality-gate status. It is JSON-serialisable so runs can be
checkpointed and replayed.
"""
from __future__ import annotations

import copy
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    DEGRADED = "degraded"


@dataclass
class StepRecord:
    name: str
    status: StepStatus = StepStatus.PENDING
    started_at: float | None = None
    finished_at: float | None = None
    duration_ms: float | None = None
    attempts: int = 0
    output: Any = None
    error: str | None = None
    degradation_level: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "attempts": self.attempts,
            "output": self.output,
            "error": self.error,
            "degradation_level": self.degradation_level,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StepRecord":
        return cls(
            name=data["name"],
            status=StepStatus(data.get("status", "pending")),
            started_at=data.get("started_at"),
            finished_at=data.get("finished_at"),
            duration_ms=data.get("duration_ms"),
            attempts=data.get("attempts", 0),
            output=data.get("output"),
            error=data.get("error"),
            degradation_level=data.get("degradation_level", 0),
        )


@dataclass
class EvidenceItem:
    """A single cited source kept in the evidence ledger."""

    source: str
    tier: int  # 1 (highest) .. 4 (lowest)
    url: str = ""
    accessed_at: str = ""
    claim: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "tier": self.tier,
            "url": self.url,
            "accessed_at": self.accessed_at,
            "claim": self.claim,
            "extra": self.extra,
        }


class PipelineState:
    """Mutable per-run state. Thread-safe enough for sequential pipelines."""

    def __init__(self, user_input: str, *, run_id: str | None = None, language: str = "en") -> None:
        self.run_id: str = run_id or uuid.uuid4().hex[:12]
        self.user_input: str = user_input
        self.language: str = language
        self.started_at: str = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.steps: list[StepRecord] = []
        self.step_outputs: dict[str, Any] = {}
        self.requirements: dict[str, Any] | None = None
        self.evidence: list[EvidenceItem] = []
        self.gates: dict[str, dict[str, Any]] = {}
        self.degradation_level: int = 0
        self.limitations: list[str] = []
        self.verdict: str | None = None
        self.metadata: dict[str, Any] = {}

    # -- step management -------------------------------------------------
    def start_step(self, name: str) -> StepRecord:
        record = StepRecord(name=name, status=StepStatus.RUNNING, started_at=time.time())
        self.steps.append(record)
        return record

    def complete_step(
        self, name: str, output: Any, *, degradation_level: int = 0, attempts: int = 1
    ) -> None:
        record = self._find(name)
        if record is None:
            record = StepRecord(name=name)
            self.steps.append(record)
        record.status = StepStatus.DEGRADED if degradation_level else StepStatus.COMPLETED
        record.finished_at = time.time()
        record.started_at = record.started_at or record.finished_at
        record.duration_ms = (record.finished_at - record.started_at) * 1000.0
        record.output = output
        record.degradation_level = degradation_level
        record.attempts = attempts
        self.step_outputs[name] = output
        if degradation_level > self.degradation_level:
            self.degradation_level = degradation_level

    def fail_step(self, name: str, error: str, *, attempts: int = 1, degradation_level: int = 0) -> None:
        record = self._find(name)
        if record is None:
            record = StepRecord(name=name)
            self.steps.append(record)
        record.status = StepStatus.FAILED
        record.finished_at = time.time()
        record.started_at = record.started_at or record.finished_at
        record.duration_ms = (record.finished_at - record.started_at) * 1000.0 if record.started_at else 0.0
        record.error = error
        record.attempts = attempts
        record.degradation_level = degradation_level
        if degradation_level > self.degradation_level:
            self.degradation_level = degradation_level

    def _find(self, name: str) -> StepRecord | None:
        for r in self.steps:
            if r.name == name:
                return r
        return None

    # -- evidence ledger -------------------------------------------------
    def add_evidence(self, item: EvidenceItem | dict[str, Any]) -> None:
        if isinstance(item, dict):
            item = EvidenceItem(**item)
        if not any(e.url == item.url and e.source == item.source for e in self.evidence if e.url):
            self.evidence.append(item)

    # -- limitations -----------------------------------------------------
    def add_limitation(self, message: str) -> None:
        if message and message not in self.limitations:
            self.limitations.append(message)

    # -- gate bookkeeping ------------------------------------------------
    def set_gate(self, gate_id: str, passed: bool, *, detail: str = "", auto_fixed: bool = False) -> None:
        self.gates[gate_id] = {"passed": passed, "detail": detail, "auto_fixed": auto_fixed}

    def gates_passed(self) -> bool:
        return all(g.get("passed") for g in self.gates.values()) if self.gates else True

    # -- serialisation ---------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "user_input": self.user_input,
            "language": self.language,
            "started_at": self.started_at,
            "degradation_level": self.degradation_level,
            "verdict": self.verdict,
            "requirements": self.requirements,
            "steps": [s.to_dict() for s in self.steps],
            "step_outputs": self.step_outputs,
            "evidence": [e.to_dict() for e in self.evidence],
            "gates": self.gates,
            "limitations": self.limitations,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, default=str)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipelineState":
        state = cls(user_input=data.get("user_input", ""), run_id=data.get("run_id"))
        state.language = data.get("language", "en")
        state.started_at = data.get("started_at", state.started_at)
        state.degradation_level = data.get("degradation_level", 0)
        state.verdict = data.get("verdict")
        state.requirements = data.get("requirements")
        state.steps = [StepRecord.from_dict(s) for s in data.get("steps", [])]
        state.step_outputs = data.get("step_outputs", {})
        state.evidence = [EvidenceItem(**e) for e in data.get("evidence", [])]
        state.gates = data.get("gates", {})
        state.limitations = data.get("limitations", [])
        state.metadata = data.get("metadata", {})
        return state

    def checkpoint(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json(), encoding="utf-8")
        return p

    def fingerprint(self) -> str:
        raw = json.dumps(self.to_dict(), sort_keys=True, default=str).encode()
        return hashlib.sha256(raw).hexdigest()[:16]


__all__ = ["PipelineState", "StepRecord", "StepStatus", "EvidenceItem"]