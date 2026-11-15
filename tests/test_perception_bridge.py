import unittest

from backend.perception_bridge import perceive


class PerceptionBridgeTests(unittest.TestCase):
    def test_maps_explicit_feeding_terms_to_documented_sugar_experiment(self):
        result = perceive("Quero comida e açúcar")
        self.assertEqual(result["intent"], "feeding")
        self.assertEqual(result["stimulus"], "sugar")
        self.assertTrue(result["connectome_mapped"])
        self.assertIn("comida", result["matched_terms"])

    def test_maps_explicit_locomotion_terms_to_documented_p9_experiment(self):
        result = perceive("Quero caminhar")
        self.assertEqual(result["intent"], "locomotion")
        self.assertEqual(result["stimulus"], "p9")

    def test_does_not_claim_arbitrary_language_is_a_connectome_stimulus(self):
        result = perceive("Explique matemática e resolva uma equação")
        self.assertIsNone(result["stimulus"])
        self.assertFalse(result["connectome_mapped"])
        self.assertEqual(result["confidence"], 0.0)

    def test_word_boundaries_avoid_false_positive_substrings(self):
        result = perceive("O movimento do arquivo")
        self.assertIsNone(result["stimulus"])

    def test_empty_input_is_safe(self):
        self.assertEqual(perceive("  ")["intent"], "empty")

    def test_flybrain_exposes_bridge_decision_without_claiming_full_connectome(self):
        from backend.fly_brain import FlyBrainCore

        state = FlyBrainCore().process("Quero comida")
        self.assertEqual(state["perception"]["stimulus"], "sugar")
        self.assertFalse(state["is_full_connectome"])



if __name__ == "__main__":
    unittest.main()
