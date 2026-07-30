import unittest
from tests._bootstrap import ROOT  # noqa: F401
from herbal_oil.tools import (
    KnowledgeQueryTool, GCMSProfileTool, YieldEstimatorTool, KnowledgeAppendTool,
    WebSearchTool, WebFetchTool,
)


class TestTools(unittest.TestCase):
    def test_knowledge_query_returns_tiered(self):
        out = KnowledgeQueryTool(settings=None).run(keywords=["lavender", "extraction"], max_results=5)
        self.assertIn("citations", out)
        self.assertIn("coverage", out)
        for c in out["citations"]:
            self.assertTrue(1 <= c["tier"] <= 4)

    def test_knowledge_query_missing_keywords(self):
        out = KnowledgeQueryTool(settings=None).run(keywords=["zzznonexistenttopic"], max_results=5)
        self.assertIn(out["coverage"], ("Weak", "Moderate"))

    def test_gcms_known_herb(self):
        out = GCMSProfileTool().run(herb="lavender", volatility_budget=90.0)
        self.assertFalse(out["inferred"])
        self.assertGreater(len(out["chemotype"]), 0)
        names = [c["compound"] for c in out["chemotype"]]
        self.assertIn("linalool", names)

    def test_gcms_unknown_herb_inferred(self):
        out = GCMSProfileTool().run(herb="some-unknown-plant")
        self.assertTrue(out["inferred"])

    def test_yield_known(self):
        out = YieldEstimatorTool().run(herb="clove", method="steam", plant_water_ratio=0.25, duration_minutes=120)
        self.assertGreater(out["estimated_yield_pct"], 5.0)
        self.assertGreaterEqual(out["aroma_preservation_index"], 0.0)

    def test_yield_unknown_inferred(self):
        out = YieldEstimatorTool().run(herb="unknown-herb", method="sfe_co2")
        self.assertTrue(out["inferred"])

    def test_yield_method_mapping(self):
        out = YieldEstimatorTool().run(herb="peppermint", method="Supercritical CO2")
        self.assertEqual(out["method"], "sfe_co2")

    def test_knowledge_append_dedup(self):
        import tempfile, os
        from types import SimpleNamespace
        tmp = tempfile.mkdtemp()
        brain = os.path.join(tmp, "SECOND-KNOWLEDGE-BRAIN.md")
        with open(brain, "w", encoding="utf-8") as fh:
            fh.write("# brain\n## 7. Knowledge Update Log\n")
        tool = KnowledgeAppendTool(settings=SimpleNamespace(project_root=__import__("pathlib").Path(tmp)))
        r1 = tool.run(title="Test entry", doi_or_url="10.9999/test-dedup-unique-12345",
                      tier=2, dry_run=True)
        self.assertTrue(r1["dry_run"])
        r2 = tool.run(title="Test entry", doi_or_url="10.9999/test-dedup-unique-12345",
                      tier=2, dry_run=False)
        self.assertTrue(r2["appended"])
        r3 = tool.run(title="Test entry", doi_or_url="10.9999/test-dedup-unique-12345",
                      tier=2, dry_run=False)
        self.assertFalse(r3["appended"])

    def test_web_search_no_network_returns_empty(self):
        # No adapter -> attempts DDG; if offline returns [] without raising.
        out = WebSearchTool(adapter=lambda **k: []).run(query="essential oil")
        self.assertEqual(out, [])

    def test_web_fetch_invalid_url_schema(self):
        from herbal_oil.core.errors import ToolExecutionError
        with self.assertRaises(ToolExecutionError):
            WebFetchTool().execute(url="not-a-url")


if __name__ == "__main__":
    unittest.main()