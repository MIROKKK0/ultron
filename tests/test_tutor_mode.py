import unittest

from backend.intent_model import resolve_intent
from backend.tutor_mode import is_programming_tutor_request


class ProgrammingTutorTests(unittest.TestCase):
    def test_natural_language_learning_request_is_detected(self):
        message = "Me ensine Python do zero com exercícios"
        self.assertTrue(is_programming_tutor_request(message))
        self.assertEqual(resolve_intent(message)["intent"], "learn_programming")

    def test_code_debugging_request_is_detected(self):
        self.assertTrue(is_programming_tutor_request("Por que este código Swift dá erro?"))

    def test_unrelated_question_is_not_tutor_mode(self):
        self.assertFalse(is_programming_tutor_request("Qual é a capital do Brasil?"))


if __name__ == "__main__":
    unittest.main()
