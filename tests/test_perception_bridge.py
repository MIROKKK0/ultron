import unittest

from backend.perception_bridge import perceive


class PerceptionBridgeTests(unittest.TestCase):
    def test_maps_explicit_positive_feeding_terms(self):
        result = perceive("Quero comida e açúcar")
        self.assertEqual(result["intent"], "feeding")
        self.assertEqual(result["stimulus"], "sugar")
        self.assertTrue(result["connectome_mapped"])

    def test_maps_explicit_positive_locomotion_terms(self):
        result = perceive("Quero caminhar")
        self.assertEqual(result["intent"], "locomotion")
        self.assertEqual(result["stimulus"], "p9")

    def test_negated_intent_is_not_sent_to_connectome(self):
        for phrase in ("Não quero comida", "Nunca vou caminhar", "Sem açúcar"):
            with self.subTest(phrase=phrase):
                result = perceive(phrase)
                self.assertIsNone(result["stimulus"])
                self.assertFalse(result["connectome_mapped"])

    def test_mixed_supported_intents_are_marked_ambiguous(self):
        result = perceive("Quero comer e caminhar")
        self.assertIsNone(result["stimulus"])
        self.assertEqual(result["intent"], "ambiguous_multiple_supported_intents")

    def test_positive_clause_after_negated_clause_is_preserved(self):
        result = perceive("Não quero comida, quero caminhar")
        self.assertEqual(result["stimulus"], "p9")

    def test_arbitrary_language_is_not_fabricated_as_neural_input(self):
        result = perceive("Explique matemática e resolva uma equação")
        self.assertIsNone(result["stimulus"])
        self.assertEqual(result["confidence"], 0.0)

    def test_word_boundaries_avoid_false_positive_substrings(self):
        self.assertIsNone(perceive("O movimento do arquivo")["stimulus"])

    def test_empty_input_is_safe(self):
        self.assertEqual(perceive("  ")["intent"], "empty")


if __name__ == "__main__":
    unittest.main()
