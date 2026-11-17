import tempfile
import unittest
from pathlib import Path

try:
    import tokenizers  # noqa: F401
except ImportError:
    tokenizers = None


@unittest.skipIf(tokenizers is None, "tokenizers is installed in the pretraining workflow")
class TrainedBPETokenizerTests(unittest.TestCase):
    def test_bpe_is_trained_from_corpus_and_round_trips_portuguese(self):
        from training.generative.train_tokenizer import train_tokenizer
        from training.generative.tokenizer import TrainedBPETokenizer
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = root / "train.txt"
            corpus.write_text(("Olá, ULTRON! A inteligência artificial aprende português.\n" * 1000), encoding="utf-8")
            output = root / "tokenizer.json"
            metadata = train_tokenizer(str(corpus), str(output), vocab_size=512, min_frequency=2)
            tokenizer = TrainedBPETokenizer(str(output))
            text = "Olá, ULTRON! Inteligência artificial e português."
            encoded = tokenizer.encode(text)
            self.assertEqual(tokenizer.decode(encoded), text)
            self.assertEqual(metadata["vocab_size"], tokenizer.vocab_size)
            self.assertGreater(tokenizer.vocab_size, 258)
            self.assertEqual(encoded[0], tokenizer.bos_id)
            self.assertEqual(encoded[-1], tokenizer.eos_id)


if __name__ == "__main__":
    unittest.main()
