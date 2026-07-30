import unittest
from tests._bootstrap import ROOT  # noqa: F401
from config.settings import (
    Settings, LLMSettings, FeatureFlags, PipelineConfig, get_settings,
    reset_settings_cache,
)


class TestConfig(unittest.TestCase):
    def setUp(self):
        reset_settings_cache()

    def test_defaults(self):
        s = Settings.from_env({})
        self.assertEqual(s.llm.provider, "claude")
        self.assertTrue(s.features.enable_cot_router)
        self.assertEqual(s.pipeline.max_steps, 6)
        self.assertIn("essential oil", s.knowledge.keywords[0].lower())

    def test_env_override(self):
        env = {"LLM_MODEL": "gpt-test", "FEATURE_WEB_TOOLS": "false",
               "PIPELINE_GATE_RETRY_LIMIT": "5", "LOG_LEVEL": "debug"}
        s = Settings.from_env(env)
        self.assertEqual(s.llm.model, "gpt-test")
        self.assertFalse(s.features.enable_web_tools)
        self.assertEqual(s.pipeline.gate_retry_limit, 5)
        self.assertEqual(s.log_level, "DEBUG")

    def test_cache(self):
        a = get_settings()
        b = get_settings()
        self.assertIs(a, b)
        reset_settings_cache()
        c = get_settings()
        self.assertIsNot(a, c)

    def test_toml(self):
        s = Settings.from_toml(ROOT / "config" / "settings.example.toml")
        self.assertEqual(s.llm.temperature, 0.2)
        self.assertEqual(s.pipeline.context_token_budget, 180000)
        self.assertTrue(s.features.enable_quality_gates)

    def test_serialise(self):
        s = Settings.from_env({})
        d = s.to_dict()
        self.assertIn("llm", d)
        self.assertIn("features", d)
        import json
        self.assertIsInstance(json.loads(s.to_json()), dict)


if __name__ == "__main__":
    unittest.main()