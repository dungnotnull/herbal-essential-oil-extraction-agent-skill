# Architecture Diagram — herbal-essential-oil-extraction v2.0

## High-level flow

```
                              USER INPUT
                                  |
                                  v
                  +-------------------------------+
                  |   Pre-Flight: language detect |
                  +-------------------------------+
                                  |
                                  v
                  +-------------------------------+
                  |   ChainOfThoughtRouter        |
                  |   intent -> ordered plan       |
                  +-------------------------------+
                                  |
        +-------------------------+-------------------------+
        |                         |                         |
        v                         v                         v
+----------------+   +----------------------+   +------------------+
| gather-        |-->| evidence-collector   |-->| core-analysis    |
| requirements   |   | (web_search, web_fetch|   | (gcms_profile,   |
|                |   |  knowledge_query)     |   |  yield_estimator)|
+----------------+   +----------------------+   +------------------+
                                                       |
                                                       v
                                    +---------------------------+
                                    | knowledge-updater         |
                                    | (knowledge_query,         |
                                    |  knowledge_append)        |
                                    +---------------------------+
                                                       |
                                                       v
                                    +---------------------------+
                                    | advisor (synthesis +      |
                                    |  risk disclosure)         |
                                    +---------------------------+
                                                       |
                                                       v
                                    +---------------------------+
                                    | Quality Gates (U1-U6,G1-G4)|
                                    |  auto-fix + 2-retry budget |
                                    +---------------------------+
                                                       |
                                                       v
                                              FINAL MARKDOWN REPORT
```

## Component map

| Layer      | Module                        | Responsibility                                 |
|------------|-------------------------------|------------------------------------------------|
| Config     | `config/settings.py`          | env/TOML settings, feature flags, LLM params  |
| Core       | `core/registry.py`            | skill registry (agents/tools/hooks by name)    |
| Core       | `core/router.py`              | chain-of-thought intent -> plan                |
| Core       | `core/runner.py`              | orchestration + quality gates + report         |
| Core       | `core/state.py`               | per-run state + evidence ledger + checkpoint   |
| Core       | `core/context.py`             | context-window budgeting + compaction         |
| Core       | `core/schemas.py`             | stdlib JSON-schema validator                    |
| Agents     | `agents/*.py`                 | 5 domain agents (deterministic solve)          |
| Tools      | `tools/*.py`                  | web/knowledge/gcms/yield tools w/ JSON schemas |
| Hooks      | `hooks/*.py`                  | lifecycle logging, state sync, event bus       |
| Knowledge  | `SECOND-KNOWLEDGE-BRAIN.md`   | living knowledge base (crawl-fed)              |
| Pipeline   | `tools/knowledge_updater.py`  | weekly crawl (ArXiv/Scholar/RSS)              |