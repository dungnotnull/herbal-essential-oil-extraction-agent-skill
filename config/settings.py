"""Type-safe, env-driven configuration for the herbal-oil skill runtime.

No third-party dependencies: pure stdlib dataclasses + TOML loader so the
runtime works in any clean Python 3.11+ environment. Every ``from_env`` accepts
an optional explicit ``env`` mapping (defaulting to ``os.environ``) so settings
are fully unit-testable without polluting the process environment.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib as _tomllib

    def _load_toml(path: Path) -> dict[str, Any]:
        with path.open("rb") as fh:
            return _tomllib.load(fh)
else:  # pragma: no cover - fallback for 3.10
    def _load_toml(path: Path) -> dict[str, Any]:
        raise RuntimeError("Python 3.11+ required for built-in tomllib")


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


_DEFAULT_ROOT = Path(__file__).resolve().parents[1]  # project root (config/ is one level down)


@dataclass
class LLMSettings:
    """LLM provider parameters. The runtime is provider-agnostic; these values
    are passed to whichever client adapter is configured."""

    provider: str = "claude"
    model: str = "claude-sonnet-4-5"
    temperature: float = 0.2
    max_tokens: int = 4096
    timeout_seconds: int = 60
    max_retries: int = 3
    fallback_model: str = "claude-haiku-4-5"

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None, prefix: str = "LLM_") -> "LLMSettings":
        e = env if env is not None else os.environ
        return cls(
            provider=e.get(prefix + "PROVIDER", "claude"),
            model=e.get(prefix + "MODEL", "claude-sonnet-4-5"),
            temperature=_as_float(e.get(prefix + "TEMPERATURE"), 0.2),
            max_tokens=_as_int(e.get(prefix + "MAX_TOKENS"), 4096),
            timeout_seconds=_as_int(e.get(prefix + "TIMEOUT_SECONDS"), 60),
            max_retries=_as_int(e.get(prefix + "MAX_RETRIES"), 3),
            fallback_model=e.get(prefix + "FALLBACK_MODEL", "claude-haiku-4-5"),
        )


@dataclass
class FeatureFlags:
    """System-wide feature flags controlling non-functional behaviour."""

    enable_cot_router: bool = True
    enable_structured_logging: bool = True
    enable_quality_gates: bool = True
    enable_degradation_banner: bool = True
    enable_knowledge_crawl: bool = True
    enable_web_tools: bool = True
    enable_cache: bool = True
    dry_run: bool = False

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None, prefix: str = "FEATURE_") -> "FeatureFlags":
        e = env if env is not None else os.environ
        return cls(
            enable_cot_router=_as_bool(e.get(prefix + "COT_ROUTER"), True),
            enable_structured_logging=_as_bool(e.get(prefix + "STRUCTURED_LOGGING"), True),
            enable_quality_gates=_as_bool(e.get(prefix + "QUALITY_GATES"), True),
            enable_degradation_banner=_as_bool(e.get(prefix + "DEGRADATION_BANNER"), True),
            enable_knowledge_crawl=_as_bool(e.get(prefix + "KNOWLEDGE_CRAWL"), True),
            enable_web_tools=_as_bool(e.get(prefix + "WEB_TOOLS"), True),
            enable_cache=_as_bool(e.get(prefix + "CACHE"), True),
            dry_run=_as_bool(e.get(prefix + "DRY_RUN"), False),
        )


@dataclass
class KnowledgeConfig:
    """Knowledge-crawl pipeline configuration (mirrors tools/knowledge_updater.py)."""

    domain: str = "Essential Oil Extraction & Aromatic Chemistry"
    keywords: list[str] = field(
        default_factory=lambda: [
            "essential oil extraction",
            "steam hydrodistillation SFE CO2",
            "GC-MS essential oil profile",
            "extraction yield parameters",
            "essential oil aroma degradation",
            "ISO 4720 essential oil standard",
        ]
    )
    max_results_per_source: int = 10
    max_new_entries_per_run: int = 20
    scoring_weights: dict[str, float] = field(
        default_factory=lambda: {
            "recency": 0.4,
            "keyword_relevance": 0.4,
            "citation_count": 0.2,
        }
    )
    schedule_academic_cron: str = "0 8 * * 1"
    schedule_news_cron: str = "0 7 * * *"

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None, prefix: str = "KNOWLEDGE_") -> "KnowledgeConfig":
        e = env if env is not None else os.environ
        kw_raw = e.get(prefix + "KEYWORDS")
        keywords = cls().keywords
        if kw_raw:
            keywords = [k.strip() for k in kw_raw.split(",") if k.strip()] or keywords
        return cls(
            keywords=keywords,
            max_results_per_source=_as_int(e.get(prefix + "MAX_RESULTS"), 10),
            max_new_entries_per_run=_as_int(e.get(prefix + "MAX_NEW"), 20),
        )


@dataclass
class PipelineConfig:
    """Pipeline orchestration parameters."""

    max_steps: int = 6
    gate_retry_limit: int = 2
    degradation_levels: int = 5
    context_token_budget: int = 180_000
    context_reserve_tokens: int = 8_000

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None, prefix: str = "PIPELINE_") -> "PipelineConfig":
        e = env if env is not None else os.environ
        return cls(
            max_steps=_as_int(e.get(prefix + "MAX_STEPS"), 6),
            gate_retry_limit=_as_int(e.get(prefix + "GATE_RETRY_LIMIT"), 2),
            degradation_levels=_as_int(e.get(prefix + "DEGRADATION_LEVELS"), 5),
            context_token_budget=_as_int(e.get(prefix + "CONTEXT_TOKEN_BUDGET"), 180_000),
            context_reserve_tokens=_as_int(e.get(prefix + "CONTEXT_RESERVE_TOKENS"), 8_000),
        )


@dataclass
class Settings:
    """Top-level runtime settings, fully resolvable from environment / TOML."""

    project_root: Path = field(default_factory=lambda: _DEFAULT_ROOT)
    log_level: str = "INFO"
    log_dir: Path = field(default_factory=lambda: Path("logs"))
    llm: LLMSettings = field(default_factory=LLMSettings)
    features: FeatureFlags = field(default_factory=FeatureFlags)
    knowledge: KnowledgeConfig = field(default_factory=KnowledgeConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.log_dir = (self.project_root / self.log_dir) if not self.log_dir.is_absolute() else self.log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["project_root"] = str(self.project_root)
        data["log_dir"] = str(self.log_dir)
        return data

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Settings":
        e = env if env is not None else os.environ
        root = Path(e.get("PROJECT_ROOT", str(_DEFAULT_ROOT)))
        log_dir = Path(e.get("LOG_DIR", "logs"))
        return cls(
            project_root=root,
            log_level=e.get("LOG_LEVEL", "INFO").upper(),
            log_dir=log_dir,
            llm=LLMSettings.from_env(e),
            features=FeatureFlags.from_env(e),
            knowledge=KnowledgeConfig.from_env(e),
            pipeline=PipelineConfig.from_env(e),
        )

    @classmethod
    def from_toml(cls, path: str | Path) -> "Settings":
        path = Path(path)
        data = _load_toml(path)
        section = data.get("tool", {}).get("herbal_oil", data.get("herbal_oil", {}))
        base = cls.from_env()
        if "log_level" in section:
            base.log_level = str(section["log_level"]).upper()
        for sub in ("llm", "features", "knowledge", "pipeline"):
            if sub in section:
                for k, v in section[sub].items():
                    setattr(getattr(base, sub), k, v)
        base.extra = {k: v for k, v in section.items() if k not in {"llm", "features", "knowledge", "pipeline"}}
        return base


_DEFAULT: Settings | None = None


def get_settings() -> Settings:
    """Return a process-cached Settings instance (env-driven)."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = Settings.from_env()
    return _DEFAULT


def reset_settings_cache() -> None:
    """Clear the cached settings (mainly for tests)."""
    global _DEFAULT
    _DEFAULT = None


__all__ = [
    "Settings",
    "LLMSettings",
    "FeatureFlags",
    "KnowledgeConfig",
    "PipelineConfig",
    "get_settings",
    "reset_settings_cache",
]