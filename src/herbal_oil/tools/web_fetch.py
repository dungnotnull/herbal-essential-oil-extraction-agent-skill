"""WebFetch tool: retrieve and clean the text content of a URL.

Returns a bounded, plain-text excerpt so downstream agents don't blow the
context budget. Falls back to an empty string with a flag on any error.
"""
from __future__ import annotations

import re
from typing import Any

from ..core.base_tool import BaseTool


class WebFetchTool(BaseTool):
    name = "web_fetch"
    description = "Fetch a URL and return cleaned plain text (truncated to max_chars). Used to read standards pages, papers, pharmacopoeia entries."
    requires_network = True
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "pattern": "^https?://", "description": "URL to fetch"},
            "max_chars": {"type": "integer", "minimum": 200, "maximum": 50000},
        },
        "required": ["url"],
        "additionalProperties": False,
    }

    def run(self, url: str, max_chars: int = 6000, **_: Any) -> dict[str, Any]:
        try:
            import requests  # type: ignore
        except ImportError:
            return {"url": url, "text": "", "ok": False, "error": "requests not installed"}
        try:
            resp = requests.get(url, timeout=30, headers={"User-Agent": "herbal-oil-skill/2.0"})
            resp.raise_for_status()
            text = re.sub(r"<script.*?</script>", " ", resp.text, flags=re.S | re.I)
            text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            return {"url": url, "text": text[:max_chars], "ok": True, "error": ""}
        except Exception as ex:
            return {"url": url, "text": "", "ok": False, "error": str(ex)}


__all__ = ["WebFetchTool"]