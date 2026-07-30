"""KnowledgeQuery tool: read SECOND-KNOWLEDGE-BRAIN.md and return tiered
citations matching a set of keywords.

Parsing is tolerant: it extracts the key-papers table rows (Section 2) plus
the appended knowledge-log entries (Section 7). Each returned item carries a
Tier label and a relevance hint so the agent can surface evidence with U3
tiering.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..core.base_tool import BaseTool

TIER_RE = re.compile(r"\b[Tt]ier\s*[:\-]?\s*([1-4])\b")
DOI_RE = re.compile(r"(10\.\d{4,9}/[^\s|)\]]+)|((?:https?|doi)://\S+)")


def _project_root(settings: Any) -> Path:
    root = getattr(settings, "project_root", None)
    if root is None:
        return Path(__file__).resolve().parents[3]
    return Path(root)


class KnowledgeQueryTool(BaseTool):
    name = "knowledge_query"
    description = "Query the SECOND-KNOWLEDGE-BRAIN.md knowledge base for tiered academic/professional citations matching keywords."
    parameters = {
        "type": "object",
        "properties": {
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "description": "Topic keywords to match against the knowledge base.",
            },
            "max_results": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "required": ["keywords"],
        "additionalProperties": False,
    }

    def run(self, keywords: list[str], max_results: int = 5, **_: Any) -> dict[str, Any]:
        root = _project_root(self.settings)
        brain = root / "SECOND-KNOWLEDGE-BRAIN.md"
        if not brain.exists():
            return {"citations": [], "gaps": ["SECOND-KNOWLEDGE-BRAIN.md not found"], "coverage": "Weak"}
        text = brain.read_text(encoding="utf-8")
        kws = [k.lower() for k in keywords if k]

        # Table rows in Section 2.
        table = re.findall(r"^\|\s*([^|\n]+?)\s*\|\s*([^|\n]+?)\s*\|\s*(\d{4})\s*\|\s*([^|\n]+?)\s*\|\s*([^|\n]+?)\s*\|\s*([1-4])\s*\|", text, re.M)
        entries: list[dict[str, Any]] = []
        for title, authors, year, venue, doi, tier in table:
            title = title.strip()
            entries.append({
                "title": title,
                "authors": authors.strip(),
                "year": year.strip(),
                "venue": venue.strip(),
                "doi": doi.strip(),
                "tier": int(tier),
                "source": "SECOND-KNOWLEDGE-BRAIN.md (Section 2)",
            })

        # Appended log entries (Section 7): each block starts with "### YYYY-MM-DD"
        for block in re.split(r"\n###\s+", text):
            if not re.match(r"\d{4}-\d{2}-\d{2}", block):
                continue
            fields = dict(re.findall(r"\*\*([^:]+):\*\*\s*([^\n]+)", block))
            tier_m = TIER_RE.search(block)
            entries.append({
                "title": block.split("\n", 1)[0].split(" — ", 1)[-1].strip() if " — " in block.split("\n", 1)[0] else block.split("\n", 1)[0].strip(),
                "authors": fields.get("Authors", "Unknown"),
                "year": fields.get("Year", ""),
                "venue": fields.get("Venue", "Unknown"),
                "doi": fields.get("DOI/URL", ""),
                "tier": int(tier_m.group(1)) if tier_m else 3,
                "source": "SECOND-KNOWLEDGE-BRAIN.md (Section 7)",
                "score": fields.get("Relevance Score", ""),
            })

        # Score by keyword overlap.
        def _score(e: dict[str, Any]) -> int:
            blob = (e.get("title", "") + " " + e.get("venue", "") + " " + e.get("authors", "")).lower()
            return sum(1 for k in kws if k in blob)

        entries.sort(key=_score, reverse=True)
        matched = [e for e in entries if _score(e) > 0] or entries
        matched = matched[:max_results]
        coverage = "Strong" if len(matched) >= 5 else "Moderate" if matched else "Weak"
        gaps = [] if matched else [f"no entries matched keywords: {kws}"]
        return {"citations": matched, "gaps": gaps, "coverage": coverage}


__all__ = ["KnowledgeQueryTool"]