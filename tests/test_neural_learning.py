import unittest

from backend.neural_learning import SparseLexicalEncoder, RewardModulatedAssociativeMemory


class NeuralLearningTests(unittest.TestCase):
    def test_encoder_is_sparse_deterministic_and_bounded(self):
        encoder = SparseLexicalEncoder(dimensions=128, max_features=12)
        encoded = encoder.encode("Mosca aprende por associação neural")
        self.assertEqual(encoded, encoder.encode("Mosca aprende por associação neural"))
        self.assertLessEqual(len(encoded), 12)
        self.assertTrue(all(0 <= key < 128 for key in encoded))
        self.assertTrue(all(0.0 < value <= 1.0 for value in encoded.values()))

    def test_reward_increases_association_and_recall(self):
        memory = RewardModulatedAssociativeMemory(learning_rate=0.2, decay=1.0)
        context, outcome = {1: 1.0, 2: 0.5}, {9: 1.0}
        memory.observe(context, outcome, 1.0)
        self.assertEqual(memory.recall(context)[0]["feature"], 9)
        self.assertGreater(memory.recall(context)[0]["activation"], 0)

    def test_negative_reward_reduces_positive_association(self):
        memory = RewardModulatedAssociativeMemory(learning_rate=0.2, decay=1.0)
        memory.observe({1: 1.0}, {2: 1.0}, 1.0)
        before = memory.recall({1: 1.0})[0]["activation"]
        memory.observe({1: 1.0}, {2: 1.0}, -1.0)
        after = memory.recall({1: 1.0})
        self.assertTrue(not after or after[0]["activation"] < before)

    def test_weights_are_bounded_and_state_round_trips(self):
        memory = RewardModulatedAssociativeMemory(learning_rate=0.25, decay=1.0)
        for _ in range(20):
            memory.observe({1: 1.0}, {2: 1.0}, 1.0)
        state = memory.state_dict()
        self.assertLessEqual(abs(state["weights"][0][2]), 1.0)
        restored = RewardModulatedAssociativeMemory()
        restored.load_state_dict(state)
        self.assertEqual(restored.state_dict(), state)

    def test_rejects_empty_and_oversized_activity(self):
        memory = RewardModulatedAssociativeMemory()
        with self.assertRaises(ValueError):
            memory.observe({}, {2: 1.0}, 1.0)
        with self.assertRaises(ValueError):
            memory.observe({i: 1.0 for i in range(49)}, {2: 1.0}, 1.0)

    def test_rejects_invalid_numeric_activity_and_rewards(self):
        memory = RewardModulatedAssociativeMemory()
        for activity in ({-1: 1.0}, {1: float("nan")}, {1: 1.1}):
            with self.subTest(activity=activity):
                with self.assertRaises(ValueError):
                    memory.observe(activity, {2: 1.0}, 1.0)
        with self.assertRaises(ValueError):
            memory.observe({1: 1.0}, {2: 1.0}, float("nan"))


if __name__ == "__main__":
    unittest.main()
