"""Project validator: checks the 8-File Contract + new v2.0 modules.

Exit code 0 = all checks pass, non-zero = failures. Superset of
`tools/run_test_scenarios.py` covering the new src/ package, config, scripts,
references, assets and SKILL.md.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

checks_passed = 0
checks_failed = 0
failures: list[str] = []


def require(cond: bool, label: str, detail: str = "") -> None:
    global checks_passed, checks_failed
    if cond:
        checks_passed += 1
    else:
        checks_failed += 1
        failures.append(f"{label}: {detail}")


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def main() -> int:
    # 1. v1 deliverables still present.
    v1 = ["CLAUDE.md", "PROJECT-detail.md", "PROJECT-DEVELOPMENT-PHASE-TRACKING.md",
          "README.md", "SECOND-KNOWLEDGE-BRAIN.md", "skills/main.md",
          "tools/knowledge_updater.py", "tools/test_knowledge_updater.py",
          "tools/run_test_scenarios.py", "tests/test-scenarios.md", "tests/TEST_RESULTS.md"]
    for f in v1:
        require((ROOT / f).exists(), f"v1.present:{f}", "missing")

    # 2. v2 directories + key files.
    v2 = [
        "SKILL.md", "pyproject.toml", "LICENSE", "requirements.txt",
        "config/settings.py", "config/__init__.py", "config/settings.example.toml",
        "src/herbal_oil/__init__.py", "src/herbal_oil/factory.py",
        "src/herbal_oil/core/registry.py", "src/herbal_oil/core/router.py",
        "src/herbal_oil/core/runner.py", "src/herbal_oil/core/base_agent.py",
        "src/herbal_oil/core/base_tool.py", "src/herbal_oil/core/base_hook.py",
        "src/herbal_oil/core/state.py", "src/herbal_oil/core/context.py",
        "src/herbal_oil/core/errors.py", "src/herbal_oil/core/logging.py",
        "src/herbal_oil/core/schemas.py",
        "src/herbal_oil/agents/__init__.py", "src/herbal_oil/agents/gather_requirements.py",
        "src/herbal_oil/agents/evidence_collector.py", "src/herbal_oil/agents/core_analysis.py",
        "src/herbal_oil/agents/knowledge_updater.py", "src/herbal_oil/agents/advisor.py",
        "src/herbal_oil/tools/__init__.py", "src/herbal_oil/tools/web_search.py",
        "src/herbal_oil/tools/web_fetch.py", "src/herbal_oil/tools/knowledge_query.py",
        "src/herbal_oil/tools/gcms_profile.py", "src/herbal_oil/tools/yield_estimator.py",
        "src/herbal_oil/tools/knowledge_append.py",
        "src/herbal_oil/hooks/__init__.py", "src/herbal_oil/hooks/lifecycle.py",
        "src/herbal_oil/hooks/state_sync.py", "src/herbal_oil/hooks/event_emitter.py",
        "references/extraction_methods.md", "references/iso_standards.md",
        "references/domain_knowledge.md", "references/prompt_templates.md",
        "assets/schemas/requirements.schema.json", "assets/schemas/evidence.schema.json",
        "assets/schemas/analysis.schema.json", "assets/schemas/knowledge.schema.json",
        "assets/schemas/advisor.schema.json", "assets/schemas/report.schema.json",
        "assets/diagrams/architecture.md",
        "scripts/setup_env.py", "scripts/seed_knowledge.py", "scripts/run_crawl.py",
        "scripts/run_pipeline.py", "scripts/validate_project.py",
    ]
    for f in v2:
        require((ROOT / f).exists(), f"v2.present:{f}", "missing")

    # 3. SKILL.md content.
    skill = read(ROOT / "SKILL.md")
    for needle in ["Skill Registry", "register", "resolve", "execute", "JSON Schema", "agents", "tools", "hooks"]:
        require(needle.lower() in skill.lower(), f"SKILL.md:{needle}", "section missing")

    # 4. JSON schemas parse.
    for sch in ["requirements", "evidence", "analysis", "knowledge", "advisor", "report"]:
        p = ROOT / "assets" / "schemas" / f"{sch}.schema.json"
        try:
            json.loads(read(p))
            require(True, f"schema.json:{sch}")
        except Exception as ex:
            require(False, f"schema.json:{sch}", str(ex))

    # 5. Import the package and build a runner.
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "config"))
    try:
        from herbal_oil.factory import build_runner

        runner = build_runner()
        require(len(runner.registry.agents) >= 5, "registry.agents>=5", f"{len(runner.registry.agents)}")
        require(len(runner.registry.tools) >= 6, "registry.tools>=6", f"{len(runner.registry.tools)}")
        require(len(runner.registry.hooks) >= 5, "registry.hooks>=5", f"{len(runner.registry.hooks)}")
    except Exception as ex:
        require(False, "package.import", str(ex))

    # 6. Tracking doc at 100%.
    pdpt = read(ROOT / "PROJECT-DEVELOPMENT-PHASE-TRACKING.md")
    require("100%" in pdpt and "Phase 6" in pdpt, "PDPT.phase6.100%", "phase 6 / 100% missing")

    total = checks_passed + checks_failed
    print(f"[validate_project] {checks_passed}/{total} checks passed")
    if failures:
        for f in failures:
            print("  - FAIL " + f)
        return 1
    print("[OK] all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())