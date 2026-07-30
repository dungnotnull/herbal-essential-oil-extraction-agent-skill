"""Local setup: validate Python version, create directories, print a config
summary. Idempotent and side-effect-light (safe to re-run)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def ensure_dirs() -> list[Path]:
    created: list[Path] = []
    for sub in ("logs", "logs/checkpoints", "logs"):
        d = ROOT / sub
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created.append(d)
    return created


def main() -> int:
    if sys.version_info < (3, 11):
        print(f"[ERROR] Python 3.11+ required (have {sys.version.split()[0]})")
        return 1
    created = ensure_dirs()
    print(f"[OK] python {sys.version.split()[0]} at {ROOT}")
    print(f"[OK] created dirs: {[str(c.relative_to(ROOT)) for c in created] or 'none (already present)'}")
    # importable check
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT))
    try:
        import herbal_oil  # noqa: F401
        from config.settings import get_settings

        s = get_settings()
        print(f"[OK] herbal_oil {herbal_oil.__version__} importable")
        print(f"[OK] settings: llm={s.llm.model} features.cot_router={s.features.enable_cot_router}")
    except Exception as ex:
        print(f"[ERROR] import failed: {ex}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())