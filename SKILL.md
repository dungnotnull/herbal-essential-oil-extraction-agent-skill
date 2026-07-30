# SKILL.md — herbal-essential-oil-extraction (v2.0)

> Skill registry & runtime contract for the **Essential Oil Extraction &
> Aromatic Chemistry** analysis harness.

This document is the authoritative reference for how skills (agents, tools,
hooks) are **registered**, **resolved**, **executed** and **validated** in the
v2.0 runtime. It supersedes the linear-only flow described in the original
markdown skills while remaining backward-compatible with them (`skills/*.md`
are now the human-readable manifests of the code under `src/herbal_oil/`).

---

## 1. Overview

The runtime is a small, dependency-free Python framework (`src/herbal_oil/`)
that implements a **modular skill-registry pattern**:

- **Agents** are domain steps (intake, evidence, core analysis, knowledge,
  advisor). Each owns a persona, a toolset, and a strict I/O JSON schema.
- **Tools** are the only side-effecting boundary (web, knowledge base,
  computation). Each exposes an OpenAI-style function descriptor.
- **Hooks** are lifecycle callbacks (logging, state sync, event bus).
- **Registry** resolves components by name at runtime.
- **Router** decides the ordered plan from intent (chain-of-thought routing).
- **Runner** orchestrates the plan, fires hooks, runs quality gates, renders
  the report.

Nothing is hardcoded in the orchestrator: registering a new agent/tool/hook
extends the skill without touching the runner.

```
USER INPUT
  -> Pre-Flight (language detect)
  -> ChainOfThoughtRouter (intent -> ordered plan)
  -> for step in plan: Registry.agent(name).solve(state)   [hooks fire]
  -> Quality Gates (U1-U6, G1-G4) with auto-fix + 2-retry budget
  -> Markdown report + JSON state
```

---

## 2. Registration

Components are registered against `SkillRegistry` by **name**. Registration is
**idempotent-safe**: duplicates raise `ValueError` (fail fast, no silent
override). Every registered component is validated for the required attributes.

| Kind   | Required attrs            | Validator                  |
|--------|---------------------------|----------------------------|
| agent  | `name`, `solve`, `output_schema` | `BaseAgent` subclass     |
| tool   | `name`, `parameters`, `run`     | JSON-schema on call args |
| hook   | `name`, `events`, dispatch     | `BaseHook` subclass      |

```python
from herbal_oil.factory import build_registry   # default wiring
from herbal_oil.core import SkillRegistry, BaseAgent, BaseTool, BaseHook

registry = SkillRegistry(settings=settings)
registry.register_tool(MyTool(settings=settings))
registry.register_agent(MyAgent(settings=settings, registry=registry))
registry.register_hook(MyHook())
```

The factory `build_registry()` (in `src/herbal_oil/factory.py`) is the canonical
wiring: it instantiates all 5 agents, 6 tools and 5 hooks and binds the
optional LLM client.

### 2.1 Resolution

Resolution is by-name and O(1):

```python
agent = registry.agent("core-analysis")     # raises AgentNotFoundError if missing
tool  = registry.tool("gcms_profile")        # raises ToolNotFoundError if missing
registry.invoke_tool("knowledge_query", keywords=["lavender"])  # executes + validates
```

`registry.manifest()` returns the full declarative manifest (OpenAI-style
function descriptors for tools; agent names + tool lists; hook events).

---

## 3. Execution

The runner executes the router plan in order. For each step:

1. Fire `on_step_start` hooks.
2. Look up the agent by name.
3. Call `agent.solve(state, **input_builder_kwargs)`.
4. On exception: retry up to 2 attempts; on final failure, mark the step
   degraded and escalate the degradation level (graceful fallback — never
   crash the pipeline).
5. Commit the result to `PipelineState` (`step_outputs[name]`, evidence
   ledger, verdict, limitations).
6. Fire `on_step_complete` (or `on_step_error`) hooks.

After the plan completes, the runner runs the **quality gates** (see §5),
escalates degradation if needed, and renders the Markdown report.

### 3.1 Deterministic-by-default

Every agent implements a deterministic `solve` path grounded in the knowledge
base and tools. When an LLM client is bound (`build_runner(llm_client=...)`),
`agent.llm_call(prompt)` enriches the narrative, with automatic
model-fallback on failure. With no client, agents degrade gracefully (Level
2-3) and still produce a structured, limitation-flagged output.

### 3.2 Comparison / repeat steps

The router sets `decision.repeats[agent_name] = N`; the runner invokes the
agent `N` times, passing `iteration` so the agent can tag the object variant
(e.g. two herbs in a comparison).

---

## 4. Validation

Validation happens at three layers:

1. **Tool argument validation** — `BaseTool.execute` validates call args
   against the tool's `parameters` JSON schema (`core/schemas.py` validator).
   Invalid args raise `ToolExecutionError` (recoverable).
2. **Agent output validation** — `BaseAgent._ok` validates the agent's output
   against its `output_schema` (the canonical copies live under
   `assets/schemas/*.schema.json`).
3. **Quality gates** — see §5.

The stdlib JSON-schema validator (`core/schemas.py`) supports the subset used
by our schemas: `type`, `required`, `properties`, `enum`, `items`,
`additionalProperties`, `minimum`, `maximum`, `minLength`, `maxLength`,
`minItems`, `pattern`, `oneOf`. Unknown keywords are ignored (forward-
compatible). `validate(instance, schema, label=...)` raises
`SchemaValidationError(errors=[...])` listing every violation.

---

## 5. Quality Gates

Ten gates: six universal (U1-U6) + four domain (G1-G4). Each gate is a
callable `(state) -> (passed: bool, detail: str, auto_fix: Callable | None)`.

| Gate | Check                                                  | Auto-fix                                   |
|------|--------------------------------------------------------|--------------------------------------------|
| U1   | >=3 sources cited, >=1 tier<=2                         | append a knowledge-base fallback source    |
| U2   | disclosure/limitations present before recommendation    | prepend standard disclosure                |
| U3   | evidence hierarchy tier (1-4) stated per source         | annotate tiers                             |
| U4   | output language matches user preference                 | run pre-flight language detection          |
| U5   | verdict present                                        | reformat                                   |
| U6   | every claim traceable or flagged                        | flag unsupported claims                     |
| G1   | method + parameters set                                 | set method/parameters                      |
| G2   | GC-MS profile & yield analyzed                          | analyze profile/yield                       |
| G3   | aroma preservation addressed                           | address aroma                              |
| G4   | ISO/pharmacopoeia standardization                       | standardize                                |

Enforcement: each gate runs, on failure the auto-fix is invoked, then it
retries up to `pipeline.gate_retry_limit` (default 2) more times. If still
failing, the gate is **fail-open**: a limitation is recorded and degradation
escalates to Level 2 — the report is still delivered with an explicit notice.

---

## 6. Hooks & Tools

### Hooks (`src/herbal_oil/hooks/`)
| Hook                  | Events                                | Purpose                          |
|-----------------------|---------------------------------------|----------------------------------|
| LoggingHook           | all lifecycle                         | structured JSON logging          |
| TimingHook            | step start/complete                   | per-step ms timing               |
| EvidenceLedgerHook    | on_evidence_added                     | tier-coerce + dedup              |
| StateCheckpointHook   | step complete / run complete          | disk checkpoint for replay       |
| EventEmitterHook      | all lifecycle                         | in-memory pub/sub event bus      |

Custom hooks subclass `BaseHook`, set `events`, override the matching
handlers, and register via `registry.register_hook(MyHook())`. Hooks must
never crash the pipeline (failures are logged and swallowed).

### Tools (`src/herbal_oil/tools/`)
| Tool              | Schema file              | Purpose                                       |
|-------------------|--------------------------|-----------------------------------------------|
| web_search        | tool.parameters          | public-web search (DuckDuckGo, no API key)    |
| web_fetch         | tool.parameters          | fetch + clean URL text (bounded)              |
| knowledge_query   | tool.parameters          | tiered citations from SECOND-KNOWLEDGE-BRAIN  |
| gcms_profile      | tool.parameters          | chemotype composition (literature-typical)    |
| yield_estimator   | tool.parameters          | yield % + aroma-preservation index            |
| knowledge_append  | tool.parameters          | dedup-append to brain Section 7               |

Each tool's `parameters` is a JSON schema; `descriptor().to_openai_schema()`
yields an OpenAI function-calling descriptor.

---

## 7. Input / Output JSON Schemas

Canonical schemas live in `assets/schemas/`. Each agent's `output_schema`
mirrors the corresponding file. Inputs to the pipeline are the user message
(string) + optional `run_id`; outputs are a `PipelineResult`:

```json
{
  "ok": true,
  "report": "# Analysis Report ...",
  "error": null,
  "decision": {"plan": ["gather-requirements", ...], "intent": "standard", "repeats": {}, "skipped": []},
  "state": { "run_id": "...", "evidence": [...], "gates": {...}, "verdict": "Optimal Extraction", ... }
}
```

See:
- `requirements.schema.json` (gather-requirements output)
- `evidence.schema.json` (evidence-collector output)
- `analysis.schema.json` (core-analysis output)
- `knowledge.schema.json` (knowledge-updater output)
- `advisor.schema.json` (advisor output)
- `report.schema.json` (top-level pipeline result)

---

## 8. Configuration

`config/settings.py` is a pure-stdlib dataclass settings tree resolvable from
environment variables or TOML (`config/settings.example.toml`):

- `LLM_*` — provider, model, temperature, max_tokens, timeout, retries, fallback
- `FEATURE_*` — boolean feature flags (cot_router, structured_logging,
  quality_gates, degradation_banner, knowledge_crawl, web_tools, cache, dry_run)
- `PIPELINE_*` — max_steps, gate_retry_limit, degradation_levels, context budgets
- `KNOWLEDGE_*` — crawl keywords, limits, scoring

`get_settings()` returns a process-cached instance; `reset_settings_cache()`
clears it (for tests).

---

## 9. Adding a New Skill

1. Implement a `BaseTool` (set `name`, `description`, `parameters`, `run`).
2. Implement a `BaseAgent` (set `name`, `persona`, `tool_names`,
   `output_schema`, implement `solve(state, **kwargs)`).
3. Add the JSON schema to `assets/schemas/` if exposing a new output contract.
4. Register both in `factory.py` (or call `register_tool`/`register_agent`).
5. Optionally add a quality gate via `runner.register_gate("Gx", fn)`.
6. Add tests under `tests/`.

No orchestrator edits are required.

---

## 10. Markdown skills (`skills/*.md`)

The `skills/*.md` files are the human-readable manifests / Claude Code skill
definitions. They describe persona, workflow, tools, output format and quality
gates for the same steps implemented in `src/herbal_oil/agents/`. When used
inside Claude Code, the agent follows the markdown; the Python runtime is the
deterministic, testable, offline-runnable implementation of the same contract.