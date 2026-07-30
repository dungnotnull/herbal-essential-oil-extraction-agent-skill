import unittest
from tests._bootstrap import ROOT  # noqa: F401
from herbal_oil.core.router import ChainOfThoughtRouter, CANONICAL_PLAN


class TestRouter(unittest.TestCase):
    def setUp(self):
        self.r = ChainOfThoughtRouter()

    def test_standard(self):
        d = self.r.route("Optimize lavender extraction yield")
        self.assertEqual(d.intent, "standard")
        self.assertEqual(d.plan, CANONICAL_PLAN)
        self.assertFalse(d.skipped)

    def test_comparison(self):
        d = self.r.route("Compare lavender vs peppermint essential oil yield")
        self.assertEqual(d.intent, "comparison")
        self.assertEqual(d.repeats.get("core-analysis"), 2)

    def test_risk(self):
        d = self.r.route("Assess risk of steam distillation thermal degradation")
        self.assertEqual(d.intent, "risk")
        self.assertIn("core-analysis", d.plan)

    def test_educational_skips_evidence(self):
        d = self.r.route("Explain how steam distillation works")
        self.assertEqual(d.intent, "educational")
        self.assertIn("evidence-collector", d.skipped)

    def test_bookends_preserved(self):
        d = self.r.route("Explain SFE CO2")
        self.assertEqual(d.plan[0], "gather-requirements")
        self.assertEqual(d.plan[-1], "advisor")


if __name__ == "__main__":
    unittest.main()