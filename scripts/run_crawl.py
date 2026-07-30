"""Thin wrapper around the existing crawl pipeline `tools/knowledge_updater.py`
so the canonical entry point lives under `scripts/`."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CRAWLER = ROOT / "tools" / "knowledge_updater.py"


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if not CRAWLER.exists():
        print(f"[ERROR] crawler not found: {CRAWLER}")
        return 1
    # Forward all args straight to knowledge_updater.py.
    sys.argv = [str(CRAWLER)] + argv
    try:
        runpy.run_path(str(CRAWLER), run_name="__main__")
        return 0
    except SystemExit as ex:
        return int(ex.code or 0)


if __name__ == "__main__":
    raise SystemExit(main())