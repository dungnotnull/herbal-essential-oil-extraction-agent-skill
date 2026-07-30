"""End-to-end pipeline CLI.

Runs the full harness on a user query and writes the Markdown report + JSON
state to disk. Useful for local validation and as an integration test target.

Usage:
    python scripts/run_pipeline.py "your query" [--out report.md] [--json state.json]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from config.settings import Settings, reset_settings_cache  # noqa: E402
from herbal_oil.factory import build_runner  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    reset_settings_cache()
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(description="Run the herbal-oil skill pipeline.")
    parser.add_argument("query", nargs="?", default="Optimize lavender essential-oil extraction yield and aroma.")
    parser.add_argument("--out", default="logs/report.md", help="Markdown report output path")
    parser.add_argument("--json", default="logs/state.json", help="Pipeline state JSON output path")
    parser.add_argument("--language", default=None, help="Force output language (en|vi)")
    args = parser.parse_args(argv)

    runner = build_runner(settings=settings)
    result = runner.run(args.query)
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(result.report, encoding="utf-8")
    json_path = ROOT / args.json
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(result.state.to_json(), encoding="utf-8")

    print(f"[{'OK' if result.ok else 'FAIL'}] verdict={result.state.verdict} "
          f"intent={result.decision.intent} degradation=L{result.state.degradation_level} "
          f"evidence={len(result.state.evidence)}")
    print(f"[OUT] {out_path}")
    print(f"[STATE] {json_path}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())