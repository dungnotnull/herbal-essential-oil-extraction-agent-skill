# TEST_RESULTS.md — Skill 289: herbal-essential-oil-extraction (v2.0.0)

## Validation Summary

| Suite | Scope | Checks | Result |
|-------|-------|--------|--------|
| `tests/run_tests.py` (unittest) | config, schemas, registry, router, tools, hooks, state/context, pipeline | 49 cases | **PASS** (exit 0) |
| `scripts/validate_project.py` | v1+v2 structural + import + manifest | 82 checks | **PASS** (exit 0) |
| `tools/test_knowledge_updater.py` | hash dedup / scoring / formatting | 3 cases | **PASS** (exit 0) |
| `tools/run_test_scenarios.py` | v1 structural & content validator | full suite | **PASS** (exit 0) |

**Overall: PRODUCTION READY v2.0.0 — all validators pass.**

## End-to-end integration

| Scenario | Intent | Verdict | Gates | Degradation |
|----------|--------|---------|-------|--------------|
| Standard lavender optimization | standard | Optimal Extraction | U1–U6,G1–G4 ✓ | L0 |
| Comparison lavender vs peppermint | comparison | — (core-analysis ×2) | exercised | L0–2 |
| Risk/thermal clove | risk | declared-set verdict | exercised | L0–1 |
| Degraded (brain unavailable) | standard | Inconclusive | limitations flagged | L≥1 |
| Vietnamese input | standard | — | language=vi | — |

## v2 unittest coverage (49 cases)
- `test_config.py` — defaults, env override, cache, TOML, serialise (5)
- `test_schemas.py` — required/enum/nested/valid instance (5)
- `test_registry.py` — register/lookup/manifest/invoke/duplicate (5)
- `test_router.py` — standard/comparison/risk/educational/bookends (5)
- `test_tools.py` — knowledge_query/gcms/yield/append/web (10)
- `test_hooks.py` — timing/evidence/event-emitter/error-swallows/checkpoint (5)
- `test_state_context.py` — step lifecycle/evidence dedup/serialise/degradation/context budget (7)
- `test_pipeline.py` — standard all-gates/output schemas/comparison/degraded/vietnamese/verdict/checkpoint (7)

## Test scenario coverage (v1, `tests/test-scenarios.md`)
5 end-to-end scenarios: standard, minimal-input, comparison, risk/conflict,
degraded-mode. All universal gates U1–U6 and domain gates G1–G4 exercised;
all verdict categories covered.