import unittest

from backend.intent_model import load_model, model_status, predict_intent, tokenize

class IntentModelTests(unittest.TestCase):
    def test_model_is_original_small_and_loaded(self):
        status = model_status()
        self.assertTrue(status["configured"])
        self.assertEqual(status["kind"], "intent_classifier")
        self.assertEqual(status["training_examples"], 225)
        self.assertFalse(status["generative_language_model"])
        self.assertLess(status["artifact_bytes"], 100_000)

    def test_custom_tokenizer_is_deterministic_and_bounded(self):
        self.assertEqual(tokenize("Olá ULTRON"), tokenize("Olá ULTRON"))
        self.assertTrue(all(0 <= key < 4096 for key in tokenize("mensagem")))

    def test_known_intents_route_to_expected_skills(self):
        cases = {
            "Oi, ULTRON": "greeting",
            "Quem é você?": "identity",
            "Planeje meu projeto em etapas": "plan",
            "Melhore sua própria arquitetura": "improve",
            "Obrigado pela ajuda": "thanks",
            "Qual seu status online?": "status",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(predict_intent(text)["intent"], expected)

    def test_unknown_open_question_is_not_misrouted_to_skill(self):
        result = predict_intent("conte uma história sobre dragões")
        self.assertEqual(result["intent"], "unknown")

if __name__ == "__main__":
    unittest.main()
