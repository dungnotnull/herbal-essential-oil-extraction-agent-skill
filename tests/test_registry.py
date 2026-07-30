import unittest
from tests._bootstrap import ROOT  # noqa: F401
from herbal_oil.core import SkillRegistry, BaseAgent, BaseTool, BaseHook, AgentNotFoundError, ToolNotFoundError, AgentResult
from herbal_oil.agents import ALL_AGENTS
from herbal_oil.tools import ALL_TOOLS
from herbal_oil.hooks import ALL_HOOKS


class TestRegistry(unittest.TestCase):
    def setUp(self):
        self.reg = SkillRegistry()

    def test_register_agents_tools_hooks(self):
        for t in ALL_TOOLS:
            self.reg.register_tool(t())
        for a in ALL_AGENTS:
            self.reg.register_agent(a())
        for h in ALL_HOOKS:
            self.reg.register_hook(h())
        self.assertEqual(len(self.reg.agents), 5)
        self.assertEqual(len(self.reg.tools), 6)
        self.assertEqual(len(self.reg.hooks), 5)
        self.assertEqual(self.reg.agent_order, list(self.reg.agents.keys()))

    def test_duplicate_raises(self):
        class T(BaseTool):
            name = "dup"
            parameters = {"type": "object"}
            def run(self, **k):
                return 1
        self.reg.register_tool(T())
        with self.assertRaises(ValueError):
            self.reg.register_tool(T())

    def test_lookup_errors(self):
        with self.assertRaises(ToolNotFoundError):
            self.reg.tool("nope")
        with self.assertRaises(AgentNotFoundError):
            self.reg.agent("nope")

    def test_manifest(self):
        for t in ALL_TOOLS:
            self.reg.register_tool(t())
        m = self.reg.manifest()
        self.assertEqual(len(m["tools"]), 6)
        self.assertEqual(m["tools"][0]["type"], "function")

    def test_invoke_tool(self):
        class T(BaseTool):
            name = "add"
            description = "add"
            parameters = {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                           "required": ["a", "b"], "additionalProperties": False}
            def run(self, a, b, **_):
                return a + b
        self.reg.register_tool(T())
        out = self.reg.invoke_tool("add", a=2, b=3)
        self.assertTrue(out["ok"])
        self.assertEqual(out["result"], 5)


if __name__ == "__main__":
    unittest.main()