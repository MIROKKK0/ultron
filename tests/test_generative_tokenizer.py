import unittest

from training.generative.tokenizer import (
    BOS_ID,
    EOS_ID,
    TOKENIZER_VERSION,
    VOCAB_SIZE,
    ByteTokenizer,
)


class GenerativeTokenizerTests(unittest.TestCase):
    def setUp(self):
        self.tokenizer = ByteTokenizer()

    def test_portuguese_and_emoji_round_trip(self):
        text = "ULTRON: ação, cérebro, iPhone 11 Pro 🚀"
        self.assertEqual(self.tokenizer.decode(self.tokenizer.encode(text)), text)

    def test_vocabulary_and_special_tokens_are_stable(self):
        self.assertEqual(TOKENIZER_VERSION, "ultron-byte-v1")
        self.assertEqual(VOCAB_SIZE, 258)
        self.assertEqual(self.tokenizer.encode("oi"), [BOS_ID, 111, 105, EOS_ID])

    def test_raw_bytes(self):
        self.assertEqual(self.tokenizer.encode("A", add_special_tokens=False), [65])

    def test_control_tokens_cannot_be_decoded_as_text_when_requested(self):
        with self.assertRaises(ValueError):
            self.tokenizer.decode([BOS_ID], skip_special_tokens=False)


if __name__ == "__main__":
    unittest.main()
