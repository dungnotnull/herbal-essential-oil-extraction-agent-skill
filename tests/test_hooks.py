import unittest
from tests._bootstrap import ROOT  # noqa: F401
from herbal_oil.core import PipelineState, BaseHook, HookContext
from herbal_oil.hooks import LoggingHook, TimingHook, EvidenceLedgerHook, EventEmitterHook, StateCheckpointHook


class TestHooks(unittest.TestCase):
    def _ctx(self, event, **payload):
        state = PipelineState(user_input="x")
        return HookContext(run_id=state.run_id, state=state, event=event, payload=payload)

    def test_timing(self):
        h = TimingHook()
        c = self._ctx("on_step_start", step="s")
        h.dispatch("on_step_start", c)
        c2 = self._ctx("on_step_complete", step="s")
        h.dispatch("on_step_complete", c2)
        self.assertIn("s", h.durations)

    def test_evidence_ledger_coerces_tier(self):
        h = EvidenceLedgerHook()
        c = self._ctx("on_evidence_added", item={"tier": 99})
        h.dispatch("on_evidence_added", c)
        self.assertEqual(c.payload["item"]["tier"], 4)

    def test_event_emitter_subscriber(self):
        h = EventEmitterHook()
        seen = []
        h.subscribe(lambda ev, rec: seen.append(ev))
        c = self._ctx("on_run_start")
        h.dispatch("on_run_start", c)
        self.assertEqual(seen, ["on_run_start"])

    def test_hook_swallows_error(self):
        class Bad(BaseHook):
            name = "bad"
            events = ("on_run_complete",)
            def on_run_complete(self, ctx):
                raise RuntimeError("boom")
        Bad().dispatch("on_run_complete", self._ctx("on_run_complete"))  # must not raise

    def test_checkpoint_writes(self):
        import tempfile
        h = StateCheckpointHook(checkpoint_dir=tempfile.mkdtemp(), every_n_steps=1)
        c = self._ctx("on_step_complete", step="s")
        h.dispatch("on_step_complete", c)
        import os
        files = os.listdir(h.checkpoint_dir)
        self.assertEqual(len(files), 1)


if __name__ == "__main__":
    unittest.main()