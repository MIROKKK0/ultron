import tempfile
import unittest
from pathlib import Path

from training.generative.prepare_corpus import clean_document


class CorpusPreparationTests(unittest.TestCase):
    def test_normalizes_and_removes_urls(self):
        result = clean_document("Ａ" * 210 + " https://example.com/test")
        self.assertIsNotNone(result)
        self.assertNotIn("https://", result)
        self.assertTrue(result.startswith("A"))

    def test_rejects_obvious_email_and_phone(self):
        self.assertIsNone(clean_document(("Texto de exemplo suficientemente longo " * 8) + " contato teste@example.com"))
        self.assertIsNone(clean_document(("Texto de exemplo suficientemente longo " * 8) + " telefone (83) 99999-9999"))

    def test_rejects_short_and_low_alpha_documents(self):
        self.assertIsNone(clean_document("texto curto"))
        self.assertIsNone(clean_document("1234567890 " * 30))

    def test_rejects_extreme_repeated_character_spam(self):
        self.assertIsNone(clean_document(("Texto válido " * 20) + ("x" * 20)))


if __name__ == "__main__":
    unittest.main()
