import unittest

from training.generative.prepare_corpus import alpha_ratio, clean_text, split_for_document


class CorpusPreparationTests(unittest.TestCase):
    def test_masks_common_direct_identifiers(self):
        text = clean_text("Contato: pessoa@example.com, CPF 123.456.789-00, telefone 11987654321")
        self.assertNotIn("pessoa@example.com", text)
        self.assertNotIn("123.456.789-00", text)
        self.assertNotIn("11987654321", text)
        self.assertIn("[EMAIL]", text)
        self.assertIn("[CPF]", text)

    def test_normalizes_unicode_and_whitespace(self):
        self.assertEqual(clean_text("  Ação   e   café  "), "Ação e café")

    def test_alpha_ratio(self):
        self.assertGreater(alpha_ratio("Texto português normal"), 0.8)
        self.assertEqual(alpha_ratio("12345 !!!"), 0.0)

    def test_document_split_is_stable(self):
        self.assertEqual(split_for_document("a" * 64), split_for_document("a" * 64))
        self.assertIn(split_for_document("b" * 64), {"train", "validation", "test"})


if __name__ == "__main__":
    unittest.main()
