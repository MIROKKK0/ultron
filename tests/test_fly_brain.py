import unittest

from backend.fly_brain import FLY_BRAIN, FlyBrainCore


class FlyBrainCoreTests(unittest.TestCase):
    def test_core_is_a_spiking_lif_microcircuit(self):
        core = FlyBrainCore(neurons_per_group=8, steps=60)
        state = core.process("investigar arquitetura neural e planejar uma tarefa", [])
        self.assertEqual(state["core"], "drosophila_lif_microcircuit")
        self.assertEqual(state["runtime"], "local_cpu_lif")
        self.assertFalse(state["is_full_connectome"])
        self.assertEqual(state["neurons"], 32)
        self.assertGreater(sum(state["spikes"].values()), 0)
        self.assertEqual(set(state["group_activity"]), {"sensory", "memory", "attention", "action"})

    def test_empty_goal_is_rejected(self):
        with self.assertRaises(ValueError):
            FlyBrainCore().process("   ")

    def test_core_keeps_short_activity_trace(self):
        core = FlyBrainCore()
        first = core.process("analisar o sistema", [])
        second = core.process("analisar o sistema", ["sistema"])
        self.assertIn("role_scores", first)
        self.assertIn("role_scores", second)
        self.assertGreaterEqual(second["memory_match"], 0.0)


    def test_core_uses_sparse_encoder_and_associative_memory(self):
        state = FlyBrainCore().process("aprendizado por recompensa", [])
        self.assertGreater(state["encoded_input_features"], 0)
        self.assertIn("associative_recall", state)
        self.assertGreaterEqual(state["association_bias"], 0.0)

    def test_global_core_is_shared(self):
        self.assertIsNotNone(FLY_BRAIN)


if __name__ == "__main__":
    unittest.main()
