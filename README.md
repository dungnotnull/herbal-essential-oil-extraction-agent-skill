# herbal-essential-oil-extraction

**Herbal Essential Oil Extraction Process Optimization** — a production-grade,
open-source skill-registry framework for **Essential Oil Extraction & Aromatic
Chemistry**.

[![Claude Skill](https://img.shields.io/badge/Claude-Skill-blue)](https://claude.ai/claude-code)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-49%20pass-brightgreen)](tests/run_tests.py)

It gathers real-time authoritative data, applies recognized domain methods,
integrates academic research, and delivers evidence-backed, risk-disclosed
outputs — through a modular, extensible, dependency-light Python runtime.

## What's new in v2.0

v1 was markdown-only (Claude Code skill definitions + a knowledge crawler).
v2.0 adds a complete, testable Python runtime implementing the same contract:

- **Skill-registry pattern** — agents, tools and hooks registered by name and
  resolved at runtime (`src/herbal_oil/core/registry.py`).
- **Chain-of-thought router** — intent → ordered plan, with comparison
  repeat-steps and educational skip (`src/herbal_oil/core/router.py`).
- **Hooks & tools** — clean lifecycle hooks (logging, state sync, event bus)
  and rich JSON-schema-backed tools (web, knowledge base, GC-MS, yield).
- **Type-safe config** — env + TOML settings, feature flags, LLM params
  (`config/`).
- **Quality gates** — U1–U6 + G1–G4 with auto-fix and a 2-retry budget.
- **Graceful degradation** — 5 levels with explicit LIMITATION banners; never
  fabricates.
- **Structured JSON logging** — machine-parseable, run-id correlated.
- **Modular directories** — `scripts/`, `references/`, `assets/`, `config/`.
- **`SKILL.md`** — the skill registry contract documentation.

The original markdown skills (`skills/*.md`) remain the human-readable Claude
Code manifests of the same steps now implemented in `src/herbal_oil/agents/`.

## Architecture

```
USER INPUT -> Pre-Flight (lang) -> ChainOfThoughtRouter -> [gather-requirements
-> evidence-collector -> core-analysis -> knowledge-updater -> advisor]
-> Quality Gates (U1-U6, G1-G4) -> Markdown report + JSON state
```

See [`assets/diagrams/architecture.md`](assets/diagrams/architecture.md) and
[`SKILL.md`](SKILL.md) for the full contract.

## Installation

```bash
pip install -e .           # install the herbal_oil package (src layout)
# or
pip install -r requirements.txt
```

## Usage

### Python runtime (deterministic, offline-runnable)
```bash
python scripts/run_pipeline.py "Optimize lavender essential-oil extraction yield and aroma"
python scripts/setup_env.py        # validate environment
python scripts/seed_knowledge.py  # seed the knowledge base baseline
python scripts/run_crawl.py --dry-run   # run the crawl pipeline (wraps tools/knowledge_updater.py)
```

```python
from herbal_oil.factory import build_runner
runner = build_runner()
result = runner.run("Compare lavender vs peppermint essential oil yield")
print(result.report)
```

### Claude Code skill
Install `skills/*.md` to `~/.claude/skills/` or use via the project `CLAUDE.md`,
then:
```
/herbal-essential-oil-extraction [your query]
```

## Configuration

Settings resolve from environment variables (or `config/settings.toml`):
- `LLM_*` — provider, model, temperature, timeout, fallback
- `FEATURE_*` — cot_router, web_tools, quality_gates, structured_logging, …
- `PIPELINE_*` — gate_retry_limit, context budgets
- `KNOWLEDGE_*` — crawl keywords, limits

See [`config/settings.example.toml`](config/settings.example.toml).

## Testing
```bash
python tests/run_tests.py                       # 49 unittest cases (stdlib)
python scripts/validate_project.py             # 82 structural checks
python tools/test_knowledge_updater.py
python tools/run_test_scenarios.py
```

## Knowledge Base
`SECOND-KNOWLEDGE-BRAIN.md` is the living, crawl-fed knowledge base updated by
`tools/knowledge_updater.py` (weekly academic + daily news schedule in
`CLAUDE.md`). In-pipeline gap-fill uses the `knowledge_append` tool.

## Data Sources
ISO 4720/4731, PhEur/USP, Industrial Crops and Products, J. Agric. Food Chem.,
Food Chemistry, J. Essential Oil Research, Molecules, Separation and
Purification Technology. See `references/` for grounding material.

## Roadmap
- [x] v1 Phase 0–5 (markdown skills + crawler) — production ready v1.0.0
- [x] v2 Phase 6 — skill-registry runtime, hooks, tools, config, scripts,
      references, assets, SKILL.md, expanded tests — production ready v2.0.0

## License
MIT — see [LICENSE](LICENSE).

## Citation
```bibtex
@software{herbal-essential-oil-extraction,
  title  = {herbal-essential-oil-extraction: Herbal Essential Oil Extraction Process Optimization},
  year   = {2026},
  version= {2.0.0}
}
```

## Why This Skill
Practitioners face fragmented data, inconsistent methodology, and tools that
don't self-improve. This skill unifies authoritative real-time data, recognized
domain methods, and a continuously-updated academic knowledge base into one
evidence-backed, risk-disclosed, self-improving workflow.