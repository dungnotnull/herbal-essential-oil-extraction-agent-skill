# DEVELOPMENT-TRACKING.md — Agent Memory (herbal-essential-oil-extraction)

> Working memory for the agent performing the v2.0 upgrade. Mirrors and
> complements `PROJECT-DEVELOPMENT-PHASE-TRACKING.md`. Updated as work proceeds.

## Objective
Upgrade, expand and complete Skill 289 to a bulletproof, production-grade,
open-source standard: flexible agent/skill architecture, hooks & tools,
`SKILL.md`, modular directories (`scripts`, `references`, `assets`, `config`),
real-world agent best practices, no placeholders, updated phase tracking at 100%.

## Decisions
- Chose a **modular skill-registry pattern** over the linear-only v1 flow:
  agents/tools/hooks registered by name and resolved at runtime.
- Added a **chain-of-thought router** (deterministic, rule-based, no LLM cost)
  that maps intent → ordered plan with comparison repeat-steps and educational
  evidence-skip.
- LLM-agnostic runtime: agents have a deterministic `solve` path grounded in
  the knowledge base + tools; an optional `llm_client` enriches narrative with
  model fallback. With no client the pipeline degrades gracefully (L2–3) and
  still produces structured, limitation-flagged output.
- Pure-stdlib config (dataclasses + tomllib) and JSON-schema validator so the
  runtime runs in any clean Python 3.11+ environment without heavy installs.
- Structured JSON logging via a `StructuredLogger` adapter that funnels kwargs
  into `extra=`; reserved key collisions (`level`, `msg`, `args`, `name`)
  guarded so they never clobber the log level.
- Quality gates are **fail-open with explicit limitation**: auto-fix + 2-retry
  budget; remaining failures escalate degradation, never crash.

## Files created (v2.0)
- `config/` — `settings.py`, `__init__.py`, `settings.example.toml`
- `src/herbal_oil/` — `__init__.py`, `factory.py`
  - `core/` — registry, router, base_agent, base_tool, base_hook, runner, state, context, errors, logging, schemas, `__init__.py`
  - `agents/` — gather_requirements, evidence_collector, core_analysis, knowledge_updater, advisor, `__init__.py`
  - `tools/` — web_search, web_fetch, knowledge_query, gcms_profile, yield_estimator, knowledge_append, `__init__.py`
  - `hooks/` — lifecycle, state_sync, event_emitter, `__init__.py`
- `assets/` — `schemas/*.schema.json` (7), `diagrams/architecture.md`
- `references/` — extraction_methods, iso_standards, domain_knowledge, prompt_templates
- `scripts/` — setup_env, seed_knowledge, run_crawl, run_pipeline, validate_project, `__init__.py`
- `tests/` — test_config, test_schemas, test_registry, test_router, test_tools, test_hooks, test_state_context, test_pipeline, run_tests, `_bootstrap.py`, `__init__.py`
- `SKILL.md`, `pyproject.toml`, `LICENSE`

## Files updated
- `CLAUDE.md`, `README.md`, `PROJECT-DEVELOPMENT-PHASE-TRACKING.md`
- `skills/main.md` + 5 `skills/sub-*.md` (added Runtime Implementation sections)

## Bugs found & fixed during build
1. `JsonFormatter` was unioning `vars(record).keys()` into the std set, hiding
   extra fields → switched to a fixed std set.
2. `StructuredLogger` kwarg `level` collided with `record.level`/levelname →
   reserved-key guard + renamed hook/runner `level=` extras to
   `degradation_level`.
3. `Settings.project_root` defaulted to `parents[2]` (= D:\972026) instead of
   `parents[1]` (project root) → fixed; nested `from_env` now thread an explicit
   `env` mapping so unit tests don't pollute the process env.
4. `knowledge_query` table-row regex required `\d{4}\|` with no trailing space
   → relaxed to `\d{4}\s*\|` and non-greedy cells; now parses the brain table.
5. `base_hook` dispatch passed `event=event` which collided with the
   `StructuredLogger` positional `event` → renamed to `hook_event`.

## Validation status (final)
- `python tests/run_tests.py` → 49 tests, OK, exit 0.
- `python scripts/validate_project.py` → 82 checks, all pass, exit 0.
- `python tools/test_knowledge_updater.py` → pass, exit 0.
- `python tools/run_test_scenarios.py` → pass, exit 0.
- End-to-end offline run → verdict Optimal Extraction, all 10 gates pass, L0.

## Status
**ALL PHASES (0–6) COMPLETE — 100% — PRODUCTION READY v2.0.0**