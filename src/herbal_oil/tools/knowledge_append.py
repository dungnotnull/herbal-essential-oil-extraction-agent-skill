"""KnowledgeAppend tool: append a new evidence entry to
SECOND-KNOWLEDGE-BRAIN.md Section 7.

This is the in-pipeline counterpart to the batch ``knowledge_updater.py``
crawl script. It dedups by DOI/URL SHA256 (case-insensitive) and never
overwrites existing content. Used by the knowledge-updater agent to commit
gap-fill finds surfaced during a run.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..core.base_tool import BaseTool


def _project_root(settings: Any) -> Path:
    root = getattr(settings, "project_root", None)
    return Path(root) if root else Path(__file__).resolve().parents[3]


def _hash(identifier: str) -> str:
    return hashlib.sha256(identifier.strip().lower().encode()).hexdigest()


class KnowledgeAppendTool(BaseTool):
    name = "knowledge_append"
    description = "Append a deduplicated evidence entry to SECOND-KNOWLEDGE-BRAIN.md Section 7 (used for gap-fill)."
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "minLength": 3},
            "authors": {"type": "string"},
            "year": {"type": "integer", "minimum": 1900, "maximum": 2100},
            "venue": {"type": "string"},
            "doi_or_url": {"type": "string", "minLength": 4},
            "tier": {"type": "integer", "minimum": 1, "maximum": 4},
            "key_finding": {"type": "string"},
            "dry_run": {"type": "boolean"},
        },
        "required": ["title", "doi_or_url", "tier"],
        "additionalProperties": False,
    }

    def run(self, title: str, doi_or_url: str, tier: int, authors: str = "Unknown",
            year: int | None = None, venue: str = "Unknown", key_finding: str = "",
            dry_run: bool = False, **_: Any) -> dict[str, Any]:
        root = _project_root(self.settings)
        brain = root / "SECOND-KNOWLEDGE-BRAIN.md"
        if not brain.exists():
            return {"appended": False, "reason": "brain file not found"}
        content = brain.read_text(encoding="utf-8")
        existing = {_hash(m) for m in re.findall(r"\*\*DOI/URL:\*\*\s*(\S+)", content)}
        existing |= {_hash(m.group(0)) for m in re.finditer(r"(10\.\d{4,9}/[^\s|)\]]+)|https?://\S+", content)}
        h = _hash(doi_or_url)
        if h in existing:
            return {"appended": False, "reason": "duplicate (already present)"}

        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        year = year or datetime.now().year
        block = (
            f"\n### {date} — {title}\n"
            f"- **Authors:** {authors}\n"
            f"- **Year:** {year}\n"
            f"- **Venue:** {venue}\n"
            f"- **DOI/URL:** {doi_or_url}\n"
            f"- **Relevance Score:** 7.0/10\n"
            f"- **Key Finding:** {key_finding or 'No abstract available.'}\n"
            f"- **Tier:** {tier}\n"
        )
        if dry_run:
            return {"appended": False, "dry_run": True, "block": block.strip()}
        if "## 7. Knowledge Update Log" not in content:
            content += "\n## 7. Knowledge Update Log\n"
        content = content.rstrip() + "\n" + block
        brain.write_text(content, encoding="utf-8")
        return {"appended": True, "title": title, "doi_or_url": doi_or_url, "tier": tier}


__all__ = ["KnowledgeAppendTool"]