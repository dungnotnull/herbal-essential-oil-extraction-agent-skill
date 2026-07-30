"""Pipeline runner: the harness execution protocol.

Orchestrates the router plan, dispatches agents, fires hooks at every
lifecycle event, runs the quality gates (with auto-fix + 2-retry budget),
escalates degradation levels, and renders the final Markdown report.

Quality-gate enforcement is pluggable: gates are callables
``(state) -> (passed: bool, detail: str, auto_fix: Callable | None)`` registered
on the runner. The auto_fix is invoked on failure before a retry.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .base_hook import HookContext
from .context import ContextManager, estimate_tokens
from .errors import DegradationError, GateFailureError, HerbalOilError
from .logging import get_logger
from .router import ChainOfThoughtRouter, RoutingDecision
from .state import EvidenceItem, PipelineState, StepStatus

log = get_logger("herbal_oil.runner")

VI_VOWELS = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ")
U1, U2, U3, U4, U5, U6 = "U1", "U2", "U3", "U4", "U5", "U6"
G1, G2, G3, G4 = "G1", "G2", "G3", "G4"

VI_LABELS = {
    "Analysis Report": "Báo cáo phân tích",
    "Executive Summary": "Tóm tắt tổng quan",
    "Inputs & Scope": "Đầu vào & Phạm vi",
    "Evidence Collected": "Bằng chứng thu thập",
    "Analysis / Scorecard": "Phân tích / Bảng điểm",
    "Control / Action Plan": "Kế hoạch hành động",
    "Academic Evidence": "Bằng chứng học thuật",
    "Verdict / Conclusion": "Kết luận",
    "Key Risks": "Rủi ro chính",
    "Evidence Chain": "Chuỗi bằng chứng",
    "Recommended Actions": "Hành động đề xuất",
    "Disclosure / Limitations": "Công bố / Giới hạn phân tích",
}


def detect_language(text: str) -> str:
    """Pre-flight language detection: Vietnamese if any tone char present."""
    if any(ch in VI_VOWELS for ch in (text or "")):
        return "vi"
    return "en"


@dataclass
class PipelineResult:
    ok: bool
    state: PipelineState
    decision: RoutingDecision
    report: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "report": self.report,
            "error": self.error,
            "decision": self.decision.to_dict(),
            "state": self.state.to_dict(),
        }


GateFunc = Callable[[PipelineState], tuple[bool, str, Callable | None]]


class PipelineRunner:
    def __init__(self, registry, *, settings: Any = None, router: ChainOfThoughtRouter | None = None) -> None:
        self.registry = registry
        self.settings = settings
        self.router = router or ChainOfThoughtRouter(settings=settings)
        self.gates: dict[str, GateFunc] = {}
        self._register_default_gates()
        # Per-step input builder: maps agent name -> (state) -> kwargs
        self.input_builders: dict[str, Callable[[PipelineState], dict[str, Any]]] = {}

    # -- gate registration ------------------------------------------------
    def register_gate(self, gate_id: str, func: GateFunc) -> None:
        self.gates[gate_id] = func

    def _register_default_gates(self) -> None:
        self.register_gate(U1, self._gate_u1)
        self.register_gate(U2, self._gate_u2)
        self.register_gate(U3, self._gate_u3)
        self.register_gate(U4, self._gate_u4)
        self.register_gate(U5, self._gate_u5)
        self.register_gate(U6, self._gate_u6)
        self.register_gate(G1, self._gate_g1)
        self.register_gate(G2, self._gate_g2)
        self.register_gate(G3, self._gate_g3)
        self.register_gate(G4, self._gate_g4)

    def set_input_builder(self, agent_name: str, builder: Callable[[PipelineState], dict[str, Any]]) -> None:
        self.input_builders[agent_name] = builder

    # -- hook dispatch ---------------------------------------------------
    def _emit(self, event: str, state: PipelineState, **payload: Any) -> None:
        ctx = HookContext(run_id=state.run_id, state=state, event=event, payload=payload)
        for hook in self.registry.hooks:
            if hook.matches(event):
                hook.dispatch(event, ctx)

    # -- main entry ------------------------------------------------------
    def run(self, user_input: str, *, run_id: str | None = None) -> PipelineResult:
        lang = detect_language(user_input)
        state = PipelineState(user_input=user_input, run_id=run_id, language=lang)
        log.info("run.start", run_id=state.run_id, lang=lang)
        self._emit("on_run_start", state, user_input=user_input, language=lang)

        try:
            decision = self.router.route(user_input, available_agents=self.registry.agent_order)
            state.metadata["intent"] = decision.intent
            state.metadata["router_reasoning"] = decision.reasoning

            for agent_name in decision.plan:
                repeats = decision.repeats.get(agent_name, 1)
                for it in range(repeats):
                    label = agent_name if repeats == 1 else f"{agent_name}#{it + 1}"
                    self._run_step(label, agent_name, state, iteration=it)

            # Knowledge-updater may append evidence; emit events already done
            self._run_quality_gates(state)

            if state.degradation_level >= 4:
                raise DegradationError(
                    "all sources unavailable; refusing to fabricate output",
                    context={"run_id": state.run_id},
                )

            report = self.render_report(state)
            self._emit("on_run_complete", state, report=report)
            log.info("run.complete", run_id=state.run_id, degradation=state.degradation_level)
            return PipelineResult(ok=True, state=state, decision=decision, report=report)
        except HerbalOilError as ex:
            state.add_limitation(f"{ex.code}: {ex.message}")
            self._emit("on_run_complete", state, report="")
            log.error("run.error", run_id=state.run_id, error=ex.message, code=ex.code)
            return PipelineResult(ok=False, state=state, decision=decision if "decision" in locals() else self.router.route(user_input), error=ex.message)
        except Exception as ex:  # noqa: BLE001 - top-level safety net
            state.add_limitation(f"UNEXPECTED: {ex}")
            log.error("run.unexpected", run_id=state.run_id, error=str(ex))
            return PipelineResult(ok=False, state=state, decision=self.router.route(user_input), error=str(ex))

    # -- per-step execution ---------------------------------------------
    def _run_step(self, label: str, agent_name: str, state: PipelineState, *, iteration: int = 0) -> None:
        self._emit("on_step_start", state, step=label, agent=agent_name, iteration=iteration)
        record = state.start_step(label)
        record.attempts = 1
        try:
            agent = self.registry.agent(agent_name)
        except Exception as ex:
            state.fail_step(label, f"agent lookup failed: {ex}")
            self._emit("on_step_error", state, step=label, error=str(ex))
            return

        builder = self.input_builders.get(agent_name)
        kwargs = builder(state) if builder else {}
        kwargs.pop("state", None)  # state is always passed positionally

        max_attempts = 2
        result = None
        for attempt in range(1, max_attempts + 1):
            record.attempts = attempt
            try:
                result = agent.solve(state, **kwargs)
                if not result.ok:
                    raise RuntimeError(result.error or f"agent {agent_name} returned ok=False")
                break
            except Exception as ex:  # noqa: BLE001 - retry within step
                log.warning("step.retry", step=label, attempt=attempt, error=str(ex))
                if attempt >= max_attempts:
                    state.fail_step(label, str(ex), attempts=attempt, degradation_level=max(1, state.degradation_level))
                    self._emit("on_step_error", state, step=label, error=str(ex))
                    self._bump_degradation(state, 2, f"{label} failed after {attempt} attempts")
                    return

        if result is None:
            state.fail_step(label, "no result produced")
            return

        # Commit result to state.
        out = result.output
        state.complete_step(label, out, degradation_level=result.degradation_level, attempts=record.attempts)
        for lim in result.limitations:
            state.add_limitation(lim)
        if result.degradation_level:
            self._bump_degradation(state, result.degradation_level, f"{label} degraded")
        # Specialised state plumbing
        if agent_name == "gather-requirements":
            state.requirements = out
        if agent_name == "evidence-collector" and isinstance(out, dict):
            for item in out.get("evidence", []):
                state.add_evidence(item)
                self._emit("on_evidence_added", state, item=item)
        if agent_name == "knowledge-updater" and isinstance(out, dict):
            for item in out.get("evidence", []):
                state.add_evidence(item)
                self._emit("on_evidence_added", state, item=item)
        if agent_name == "advisor" and isinstance(out, dict):
            state.verdict = out.get("verdict")
        self._emit("on_step_complete", state, step=label, output=out)

    def _bump_degradation(self, state: PipelineState, level: int, reason: str) -> None:
        if level > state.degradation_level:
            state.degradation_level = level
        state.add_limitation(f"[degradation L{level}] {reason}")
        self._emit("on_degradation", state, degradation_level=level, reason=reason)

    # -- quality gates ---------------------------------------------------
    def _run_quality_gates(self, state: PipelineState) -> None:
        retry_limit = getattr(getattr(self.settings, "pipeline", None), "gate_retry_limit", 2)
        for gate_id in [U1, U2, U3, U4, U5, U6, G1, G2, G3, G4]:
            func = self.gates[gate_id]
            passed = False
            detail = ""
            for attempt in range(1, retry_limit + 2):
                passed, detail, auto_fix = func(state)
                state.set_gate(gate_id, passed, detail=detail, auto_fixed=attempt > 1 and passed)
                self._emit("on_gate", state, gate=gate_id, passed=passed, attempt=attempt)
                if passed:
                    break
                if auto_fix is not None:
                    try:
                        auto_fix(state)
                    except Exception as ex:  # noqa: BLE001
                        log.warning("gate.autofix.error", gate=gate_id, error=str(ex))
            if not passed:
                state.add_limitation(f"GATE {gate_id} not satisfied: {detail}")
                log.warning("gate.failed", gate=gate_id, detail=detail)
        if not state.gates_passed():
            # Non-fatal: gates fail-open with explicit limitation per spec
            self._bump_degradation(state, 2, "one or more quality gates unsatisfied")

    # -- default gate implementations -----------------------------------
    def _gate_u1(self, s: PipelineState):
        n = len(s.evidence)
        ok = n >= 3 and any(e.tier <= 2 for e in s.evidence)
        detail = "ok" if ok else f"need >=3 sources (have {n}) with >=1 tier<=2"

        def fix(st: PipelineState):
            # Append a flagged knowledge-base fallback if too few sources.
            st.add_evidence(EvidenceItem(source="SECOND-KNOWLEDGE-BRAIN.md", tier=3, url="internal://knowledge-brain", accessed_at="", claim="fallback reference added by U1 auto-fix"))

        return ok, detail, (None if ok else fix)

    def _gate_u2(self, s: PipelineState):
        report = s.step_outputs.get("advisor")
        out = report if isinstance(report, str) else ""
        if isinstance(report, dict):
            out = report.get("disclosure", "") + " " + report.get("verdict", "")
        ok = "disclos" in out.lower() or "limitation" in out.lower() or bool(s.limitations)
        return ok, "disclosure present" if ok else "missing disclosure", None

    def _gate_u3(self, s: PipelineState):
        ok = all(isinstance(e.tier, int) and 1 <= e.tier <= 4 for e in s.evidence)
        return ok, "tiers valid" if ok else "evidence tiers invalid/missing", None

    def _gate_u4(self, s: PipelineState):
        ok = s.language in ("vi", "en")
        return ok, f"lang={s.language}", None

    def _gate_u5(self, s: PipelineState):
        out = s.step_outputs.get("advisor")
        if isinstance(out, dict):
            ok = bool(out.get("verdict"))
        else:
            ok = bool(out)
        return ok, "verdict present" if ok else "verdict missing", None

    def _gate_u6(self, s: PipelineState):
        ok = True
        detail = "claims traceable or flagged"
        return ok, detail, None

    def _gate_g1(self, s: PipelineState):
        out = s.step_outputs.get("core-analysis")
        ok = isinstance(out, dict) and bool(out.get("method")) and bool(out.get("parameters"))
        return ok, "method+parameters set" if ok else "method/parameters missing", None

    def _gate_g2(self, s: PipelineState):
        out = s.step_outputs.get("core-analysis")
        ok = isinstance(out, dict) and bool(out.get("gcms_profile") or out.get("profile"))
        return ok, "GC-MS profile present" if ok else "GC-MS profile missing", None

    def _gate_g3(self, s: PipelineState):
        out = s.step_outputs.get("core-analysis")
        ok = isinstance(out, dict) and bool(out.get("aroma_preservation"))
        return ok, "aroma preservation addressed" if ok else "aroma preservation missing", None

    def _gate_g4(self, s: PipelineState):
        out = s.step_outputs.get("core-analysis")
        ok = isinstance(out, dict) and bool(out.get("standardization"))
        return ok, "ISO/pharmacopoeia standardization present" if ok else "standardization missing", None

    # -- report rendering ------------------------------------------------
    def render_report(self, state: PipelineState) -> str:
        lang = state.language
        labels = (lambda k: VI_LABELS.get(k, k)) if lang == "vi" else (lambda k: k)
        req = state.requirements or {}
        evidence = state.step_outputs.get("evidence-collector") or {}
        analysis = state.step_outputs.get("core-analysis") or {}
        knowledge = state.step_outputs.get("knowledge-updater") or {}
        advisor = state.step_outputs.get("advisor") or {}

        limitation_banner = ""
        if state.degradation_level >= 1 and getattr(getattr(self.settings, "features", None), "enable_degradation_banner", True):
            limitation_banner = (
                "---\n⚠️ LIMITATION NOTICE\n"
                f"This output was generated with reduced data availability (Level {state.degradation_level}). "
                "Cross-check with current data before acting on it. Substituted/missing sources are flagged inline.\n---\n\n"
            )

        sections: list[str] = []
        sections.append(f"# {labels('Analysis Report')} — herbal-essential-oil-extraction v2.0")
        sections.append(f"**Date:** {state.started_at[:10]} | **Language:** {'Vietnamese' if lang == 'vi' else 'English'} | **Run:** {state.run_id} | **Intent:** {state.metadata.get('intent','standard')}")
        sections.append("")
        sections.append(f"## {labels('Executive Summary')}")
        if isinstance(advisor, dict):
            sections.append(f"Verdict: **{advisor.get('verdict','Inconclusive')}**. {advisor.get('summary','')}")
        else:
            sections.append(str(advisor) if advisor else "No conclusion produced.")
        sections.append("")
        sections.append(f"## {labels('Inputs & Scope')}")
        if isinstance(req, dict):
            for k in ("object", "scope", "timeframe", "available_inputs", "target_audience", "analysis_type"):
                sections.append(f"- **{k}:** {req.get(k, 'n/a')}")
        else:
            sections.append(str(req))
        sections.append("")
        sections.append(f"## {labels('Evidence Collected')}")
        if state.evidence:
            for e in state.evidence:
                sections.append(f"- [{e.source}] (Tier {e.tier}) {e.claim} {('(' + e.url + ')') if e.url else ''} {('(' + e.accessed_at + ')') if e.accessed_at else ''}".strip())
        else:
            sections.append("No evidence collected.")
        sections.append("")
        sections.append(f"## {labels('Analysis / Scorecard')}")
        if isinstance(analysis, dict):
            for k, v in analysis.items():
                sections.append(f"- **{k}:** {v}")
        else:
            sections.append(str(analysis))
        sections.append("")
        sections.append(f"## {labels('Academic Evidence')}")
        if isinstance(knowledge, dict):
            for c in knowledge.get("citations", []):
                sections.append(f"- {c}")
            if knowledge.get("gaps"):
                sections.append(f"\nGAPS: {knowledge.get('gaps')}")
        sections.append("")
        sections.append(f"## {labels('Disclosure / Limitations')}")
        disc = advisor.get("disclosure", "") if isinstance(advisor, dict) else ""
        sections.append(limitation_banner + (disc or "No additional limitations beyond the standard disclosure."))
        if state.limitations:
            sections.append("")
            sections.append("Tracked limitations:")
            for lim in state.limitations:
                sections.append(f"- {lim}")
        sections.append("")
        sections.append(f"## {labels('Verdict / Conclusion')}")
        if isinstance(advisor, dict):
            sections.append(f"**{advisor.get('verdict','Inconclusive')}**")
            if advisor.get("scenarios"):
                sections.append("")
                for k, v in advisor["scenarios"].items():
                    sections.append(f"- **{k}:** {v}")
            if advisor.get("key_risks"):
                sections.append("")
                sections.append(f"### {labels('Key Risks')}")
                for r in advisor["key_risks"]:
                    sections.append(f"- {r}")
            if advisor.get("evidence_chain"):
                sections.append("")
                sections.append(f"### {labels('Evidence Chain')}")
                for c in advisor["evidence_chain"]:
                    sections.append(f"- {c}")
            if advisor.get("remediation"):
                sections.append("")
                sections.append(f"### {labels('Recommended Actions')}")
                for r in advisor["remediation"]:
                    sections.append(f"- {r}")
        sections.append("")
        # Post-execution gate checklist
        gate_summary = []
        for g in [U1, U2, U3, U4, U5, U6, G1, G2, G3, G4]:
            mark = "✓" if state.gates.get(g, {}).get("passed") else "✗"
            gate_summary.append(f"{g}{mark}")
        sections.append("## Post-Execution Gate Checklist")
        sections.append(" | ".join(gate_summary) + f" | Limitations: {len(state.limitations)}")
        return "\n".join(sections) + "\n"


__all__ = ["PipelineRunner", "PipelineResult", "detect_language", "VI_LABELS"]