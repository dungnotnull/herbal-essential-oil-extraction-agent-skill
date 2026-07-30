"""End-to-end pipeline integration tests."""
import unittest
from tests._bootstrap import ROOT  # noqa: F401
from config.settings import Settings
from herbal_oil.core.logging import configure_logging
from herbal_oil.core.schemas import load_schema, validate
from herbal_oil.factory import build_runner


def _offline_settings():
    s = Settings.from_env({})
    s.features.enable_web_tools = False  # deterministic, no network
    s.features.enable_structured_logging = False
    return s


class TestPipeline(unittest.TestCase):
    def setUp(self):
        configure_logging("WARNING", structured=False, force=True)

    def test_standard_run_all_gates_pass(self):
        runner = build_runner(settings=_offline_settings())
        res = runner.run("Optimize steam distillation yield and aroma for lavender essential oil, lab-to-pilot scale")
        self.assertTrue(res.ok, msg=res.error)
        self.assertEqual(res.decision.intent, "standard")
        self.assertEqual(res.state.verdict, "Optimal Extraction")
        self.assertGreaterEqual(len(res.state.evidence), 3)
        for gate, info in res.state.gates.items():
            self.assertTrue(info["passed"], msg=f"gate {gate} failed: {info['detail']}")
        self.assertGreater(len(res.report), 200)

    def test_output_schemas(self):
        runner = build_runner(settings=_offline_settings())
        res = runner.run("Optimize peppermint essential oil extraction")
        schemas = {
            "core-analysis": "analysis.schema.json",
            "advisor": "advisor.schema.json",
            "knowledge-updater": "knowledge.schema.json",
        }
        for step, fname in schemas.items():
            schema = load_schema(ROOT / "assets" / "schemas" / fname)
            validate(res.state.step_outputs[step], schema, label=step)

    def test_comparison_runs_core_twice(self):
        runner = build_runner(settings=_offline_settings())
        res = runner.run("Compare lavender vs peppermint essential oil yield and aroma")
        self.assertEqual(res.decision.intent, "comparison")
        self.assertEqual(res.decision.repeats.get("core-analysis"), 2)
        core_steps = [s for s in res.state.steps if s.name.startswith("core-analysis")]
        self.assertEqual(len(core_steps), 2)

    def test_degraded_when_no_evidence(self):
        # Force evidence failure by pointing knowledge_query at a missing brain
        # via a settings object whose project_root has no brain.
        import tempfile, os
        from types import SimpleNamespace
        s = _offline_settings()
        runner = build_runner(settings=s)
        # Override the knowledge_query tool's project root to a temp dir w/o brain.
        for t in runner.registry.tools.values():
            if t.name == "knowledge_query":
                t.settings = SimpleNamespace(project_root=__import__("pathlib").Path(tempfile.mkdtemp()))
        res = runner.run("Optimize extraction for lavender")
        self.assertGreaterEqual(res.state.degradation_level, 1)
        self.assertTrue(res.state.limitations)

    def test_vietnamese_detected(self):
        runner = build_runner(settings=_offline_settings())
        res = runner.run("Ối ưu hóa chiết xuất tinh dầu hoa oải hương")
        self.assertEqual(res.state.language, "vi")

    def test_advisor_verdict_in_declared_set(self):
        runner = build_runner(settings=_offline_settings())
        res = runner.run("Explain risk of thermal degradation in clove steam distillation")
        self.assertIn(res.state.verdict, ["Optimal Extraction", "Conditional (thermal)", "Yield/Aroma Loss", "Inconclusive"])

    def test_state_checkpoint_written(self):
        import tempfile, os
        from herbal_oil.hooks.state_sync import StateCheckpointHook
        runner = build_runner(settings=_offline_settings())
        # Replace checkpoint hook with a temp dir.
        for h in runner.registry.hooks:
            if isinstance(h, StateCheckpointHook):
                h.checkpoint_dir = tempfile.mkdtemp()
                h.every_n_steps = 1
        res = runner.run("Optimize lemongrass extraction")
        self.assertTrue(res.ok)
        files = os.listdir(runner.registry.hooks[0].__class__ and [h for h in runner.registry.hooks if isinstance(h, StateCheckpointHook)][0].checkpoint_dir)
        self.assertGreaterEqual(len(files), 1)


if __name__ == "__main__":
    unittest.main()