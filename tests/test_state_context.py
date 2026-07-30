import unittest
from tests._bootstrap import ROOT  # noqa: F401
from herbal_oil.core import PipelineState, StepStatus, EvidenceItem, ContextManager, estimate_tokens
from herbal_oil.core.errors import ContextBudgetExceeded


class TestState(unittest.TestCase):
    def test_step_lifecycle(self):
        s = PipelineState(user_input="x")
        s.start_step("a")
        s.complete_step("a", {"k": 1})
        self.assertEqual(s.step_outputs["a"], {"k": 1})
        self.assertEqual(s.steps[0].status, StepStatus.COMPLETED)

    def test_evidence_dedup(self):
        s = PipelineState(user_input="x")
        s.add_evidence(EvidenceItem(source="A", tier=2, url="u1"))
        s.add_evidence(EvidenceItem(source="A", tier=2, url="u1"))
        self.assertEqual(len(s.evidence), 1)

    def test_serialise_roundtrip(self):
        s = PipelineState(user_input="x")
        s.add_evidence(EvidenceItem(source="A", tier=1, url="u"))
        s.set_gate("U1", True)
        d = s.to_dict()
        s2 = PipelineState.from_dict(d)
        self.assertEqual(s2.evidence[0].source, "A")
        self.assertTrue(s2.gates["U1"]["passed"])

    def test_degradation_tracking(self):
        s = PipelineState(user_input="x")
        s.fail_step("a", "err", degradation_level=2)
        self.assertEqual(s.degradation_level, 2)
        self.assertEqual(s.steps[0].status, StepStatus.FAILED)
        self.assertTrue(s.steps[0].error)


class TestContext(unittest.TestCase):
    def test_budget_enforce_compacts(self):
        cm = ContextManager(budget_tokens=100, reserve_tokens=20)
        for i in range(30):
            cm.add("user", "x" * 20, essential=(i % 2 == 0))
        cm.enforce()
        self.assertLessEqual(cm.total_tokens(), cm.usable)

    def test_budget_exceeded_raises(self):
        cm = ContextManager(budget_tokens=40, reserve_tokens=10)
        cm.add("user", "y" * 500, essential=True)
        with self.assertRaises(ContextBudgetExceeded):
            cm.enforce()

    def test_estimate_tokens(self):
        self.assertGreater(estimate_tokens("abcd"), 0)
        self.assertEqual(estimate_tokens(None), 0)


if __name__ == "__main__":
    unittest.main()