import unittest

from training.tokenizer import BOS_ID, EOS_ID, TOKENIZER_VERSION, VOCAB_SIZE, ByteTokenizer


class ByteTokenizerTests(unittest.TestCase):
    def setUp(self):
        self.tokenizer = ByteTokenizer()

    def test_round_trip_portuguese_and_unicode(self):
        sample = "ULTRON: ação, cérebro, iPhone 11 Pro 🚀"
        self.assertEqual(self.tokenizer.decode(self.tokenizer.encode(sample)), sample)

    def test_special_tokens_are_versioned_and_reserved(self):
        self.assertEqual(TOKENIZER_VERSION, "ultron-byte-v1")
        self.assertEqual(VOCAB_SIZE, 258)
        self.assertEqual(self.tokenizer.encode("oi"), [BOS_ID, 111, 105, EOS_ID])

    def test_raw_bytes_can_be_encoded_without_special_tokens(self):
        self.assertEqual(self.tokenizer.encode("A", add_special_tokens=False), [65])

    def test_empty_text_round_trips(self):
        self.assertEqual(self.tokenizer.decode(self.tokenizer.encode("")), "")


if __name__ == "__main__":
    unittest.main()
