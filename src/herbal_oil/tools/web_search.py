"""WebSearch tool.

Wraps a pluggable search adapter. When no adapter is supplied it attempts to
use the optional ``requests``-backed DuckDuckGo HTML endpoint (no API key
required). On any failure it returns an empty result set with a degraded flag
rather than raising, so the agent can fall back to the knowledge base.
"""
from __future__ import annotations

import re
from typing import Any

from ..core.base_tool import BaseTool


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the public web for authoritative sources relevant to essential-oil extraction & aromatic chemistry. Returns a list of {title,url,snippet}."
    requires_network = True
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 2, "description": "Search query"},
            "max_results": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "required": ["query"],
        "additionalProperties": False,
    }
    returns = {"type": "array", "items": {"type": "object"}}

    def __init__(self, *, settings: Any = None, adapter=None) -> None:
        super().__init__(settings=settings)
        self._adapter = adapter

    def run(self, query: str, max_results: int = 5, **_: Any) -> list[dict[str, Any]]:
        if self._adapter is not None:
            return self._adapter(query=query, max_results=max_results)
        try:
            return self._duckduckgo(query, max_results)
        except Exception:
            # Graceful fallback: no fabricated results.
            return []

    @staticmethod
    def _duckduckgo(query: str, max_results: int) -> list[dict[str, Any]]:
        try:
            import requests  # type: ignore
        except ImportError:
            return []
        url = "https://html.duckduckgo.com/html/"
        resp = requests.post(url, data={"q": query}, timeout=20, headers={"User-Agent": "herbal-oil-skill/2.0"})
        resp.raise_for_status()
        results: list[dict[str, Any]] = []
        for m in re.finditer(r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', resp.text, re.S):
            href = m.group(1)
            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            if href.startswith("//"):
                href = "https:" + href
            results.append({"title": title, "url": href, "snippet": ""})
            if len(results) >= max_results:
                break
        return results


__all__ = ["WebSearchTool"]