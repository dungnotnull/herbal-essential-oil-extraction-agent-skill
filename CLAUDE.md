# CLAUDE.md — Skill 289: herbal-essential-oil-extraction

## Skill Identity
- **Skill Name:** `herbal-essential-oil-extraction`
- **Tagline:** Herbal Essential Oil Extraction Process Optimization — Essential Oil Extraction & Aromatic Chemistry analysis & decision-support harness.
- **Version:** 2.0.0 (production-ready skill-registry runtime)
- **Folder:** `D:\972026\289-herbal-essential-oil-extraction\`

---

## Problem This Skill Solves

This skill provides a structured, evidence-backed analytical workflow for
**Essential Oil Extraction & Aromatic Chemistry**. It gathers authoritative
real-time and reference data, applies recognized domain methods, cross-references
academic research, and delivers actionable outputs that are fully evidenced,
risk/limitation-disclosed, and traceable to authoritative sources — continuously
self-improving through an automated knowledge crawl pipeline.

---

## Two complementary implementations

| Layer | Path | Purpose |
|-------|------|---------|
| **Markdown skill manifests** | `skills/*.md` | Human-readable Claude Code skill definitions (persona, workflow, output format, quality gates). |
| **Python runtime** | `src/herbal_oil/` | Deterministic, testable, offline-runnable implementation of the same contract (registry, router, agents, tools, hooks, runner). |

Both describe the same 5-step harness; the markdown is the spec, the Python is
the executable reference.

## Harness Flow Summary

```
/herbal-essential-oil-extraction invoked
  -> Pre-Flight: language detect (vi|en)
  -> ChainOfThoughtRouter: intent -> ordered plan (standard|comparison|risk|educational)
  -> Step 1: sub-gather-requirements  -> structured requirements
  -> Step 2: sub-evidence-collector   -> tiered evidence bundle
  -> Step 3: sub-core-analysis        -> method + parameters + GC-MS + yield + aroma + ISO
  -> Step 4: sub-knowledge-updater    -> 3-5 tiered citations + flagged gaps
  -> Step 5: sub-advisor              -> risk-disclosed verdict + evidence chain
  -> Step 6: Quality Gates (U1-U6 + G1-G4) with auto-fix + 2-retry budget
```

## Sub-Skills (markdown manifests)

| File | Purpose |
|------|---------|
| `skills/main.md` | Harness entry point + quality gates + degradation |
| `skills/sub-gather-requirements.md` | Intake: object/scope/timeframe/audience/language |
| `skills/sub-evidence-collector.md` | Tiered evidence bundle (KB anchor + live web) |
| `skills/sub-core-analysis.md` | Method/parameters/profile/yield/aroma/ISO |
| `skills/sub-knowledge-updater.md` | Tiered citations + crawl gap flags |
| `skills/sub-advisor.md` | Risk-disclosed conclusion + evidence chain |

## Runtime Components (src/herbal_oil)

| Module | Responsibility |
|--------|----------------|
| `core/registry.py` | skill registry (agents/tools/hooks by name) |
| `core/router.py` | chain-of-thought intent -> plan |
| `core/runner.py` | orchestration + quality gates + report |
| `core/state.py` | per-run state + evidence ledger + checkpoints |
| `core/context.py` | context-window budgeting + compaction |
| `core/schemas.py` | stdlib JSON-schema validator |
| `core/logging.py` | structured JSON logging |
| `core/errors.py` | error hierarchy with graceful fallback |
| `agents/*.py` | 5 domain agents (deterministic solve) |
| `tools/*.py` | web_search, web_fetch, knowledge_query, gcms_profile, yield_estimator, knowledge_append |
| `hooks/*.py` | logging, timing, evidence-ledger, state-checkpoint, event-emitter |
| `factory.py` | declarative wiring -> build_runner() |

See `SKILL.md` for the full registry contract.

## Tools Required (Claude Code manifest)
- **WebSearch** — live domain news, reports, standards updates
- **WebFetch** — scrape authoritative sources
- **Read / Write** — read SECOND-KNOWLEDGE-BRAIN.md; append knowledge entries
- **Bash** — run `tools/knowledge_updater.py` / `scripts/*`
- **Skill** — invoke sub-skills sequentially through the harness

## Knowledge Sources

### Domain Authoritative
- ISO 4720/4731 essential oil standards, PhEur/USP, GC-MS analysis, yield/quality refs.

### Academic & Research
- Industrial Crops and Products (Elsevier), J. Agric. Food Chem. (ACS),
  Food Chemistry (Elsevier), J. Essential Oil Research (T&F), Molecules (MDPI),
  Separation and Purification Technology (Elsevier).

### Academic Crawl Targets
- Semantic Scholar / ArXiv keyword clusters (see `KNOWLEDGE_CONFIG`).

## Supporting Python Tools

| File | Purpose |
|------|---------|
| `tools/knowledge_updater.py` | Crawl pipeline (ArXiv/Scholar/RSS -> brain) |
| `tools/test_knowledge_updater.py` | unit tests (hash, score, format) |
| `tools/run_test_scenarios.py` | v1 structural & content validator |
| `scripts/setup_env.py` | environment validation |
| `scripts/seed_knowledge.py` | seed baseline knowledge entries |
| `scripts/run_crawl.py` | wrapper around the crawl pipeline |
| `scripts/run_pipeline.py` | end-to-end pipeline CLI |
| `scripts/validate_project.py` | v2 structural validator (82 checks) |

## Automated Knowledge Update Schedule

```cron
# Weekly academic update (Mondays 8:00 AM)
0 8 * * 1 python D:/972026/289-herbal-essential-oil-extraction/scripts/run_crawl.py >> logs/knowledge_update.log 2>&1

# Daily news update (Daily 7:00 AM)
0 7 * * * python D:/972026/289-herbal-essential-oil-extraction/scripts/run_crawl.py --news-only >> logs/knowledge_news.log 2>&1
```

Manual: `python scripts/run_crawl.py --dry-run` | `--keywords "..."` | `--news-only`

## Active Development Tasks

- [x] v1 Phase 0–5 (markdown skills + crawler) — production ready v1.0.0
- [x] v2 Phase 6 — skill-registry runtime, hooks, tools, config, scripts,
      references, assets, SKILL.md, expanded tests — production ready v2.0.0

## References

- `PROJECT-detail.md` — full technical specification
- `PROJECT-DEVELOPMENT-PHASE-TRACKING.md` — build roadmap
- `SKILL.md` — skill registry contract
- `SECOND-KNOWLEDGE-BRAIN.md` — self-improving knowledge base
- `assets/diagrams/architecture.md` — architecture diagram
- `references/` — domain knowledge, prompt templates, ISO standards
- `D:\972026\SKILL-STANDARD.md` — library-wide standard