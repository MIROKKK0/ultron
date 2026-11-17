import argparse
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
            corpus.write_text(("Olá, ULTRON! A inteligência artificial aprende português.\n" * 3000), encoding="utf-8")
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

    def test_bpe_training_pipeline_saves_matching_tokenizer_metadata(self):
        import torch
        from training.generative.train import train
        from training.generative.train_tokenizer import train_tokenizer
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = root / "train.txt"
            validation = root / "validation.txt"
            test = root / "test.txt"
            repeated = "O ULTRON aprende português com dados públicos e validação. "
            corpus.write_text(repeated * 3000, encoding="utf-8")
            validation.write_text("A inteligência artificial aprende com exemplos separados. " * 200, encoding="utf-8")
            test.write_text("O teste mede a generalização em português brasileiro. " * 200, encoding="utf-8")
            tokenizer_path = root / "tokenizer.json"
            train_tokenizer(str(corpus), str(tokenizer_path), vocab_size=512, min_frequency=2)
            args = argparse.Namespace(
                steps=2, batch_size=2, eval_batches=1, eval_interval=1, threads=1,
                warmup_steps=1, min_lr_ratio=0.1, seed=19, corpus=str(corpus),
                validation_corpus=str(validation), test_corpus=str(test),
                context_length=16, validation_fraction=0.1, width=16, layers=1, heads=2,
                learning_rate=3e-4, early_stopping_patience=0, min_delta=0.0,
                output=str(root / "checkpoint.pt"), tokenizer_json=str(tokenizer_path),
            )
            result = train(args)
            checkpoint = torch.load(root / "checkpoint.pt", map_location="cpu", weights_only=True)
            self.assertEqual(result["tokenizer"], "ultron-bpe-v1")
            self.assertEqual(checkpoint["tokenizer_version"], "ultron-bpe-v1")
            self.assertEqual(checkpoint["model_config"]["vocab_size"], checkpoint["tokenizer_vocab_size"])
            self.assertGreater(result["validation_bits_per_byte"], 0)
            self.assertGreater(result["test_bits_per_byte"], 0)


if __name__ == "__main__":
    unittest.main()
