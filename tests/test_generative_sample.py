import tempfile
import unittest
from pathlib import Path

try:
    import torch
    import tokenizers
except ImportError:
    torch = None
    tokenizers = None


@unittest.skipIf(torch is None or tokenizers is None, "Optional training dependencies are installed in model workflows")
class GenerativeSamplingTests(unittest.TestCase):
    def test_sampling_requires_matching_tokenizer_and_returns_auditable_samples(self):
        from training.generative.model import ModelConfig, UltronTinyGPT
        from training.generative.sample import generate_samples
        from training.generative.train_tokenizer import train_tokenizer
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = root / "train.txt"
            corpus.write_text(("ULTRON aprende português com dados públicos e testes.\n" * 3000), encoding="utf-8")
            tokenizer_path = root / "tokenizer.json"
            metadata = train_tokenizer(str(corpus), str(tokenizer_path), vocab_size=512)
            model = UltronTinyGPT(ModelConfig(vocab_size=metadata["vocab_size"], context_length=32, width=16, layers=1, heads=2))
            import hashlib
            checkpoint_path = root / "model.pt"
            torch.save({
                "model_state": model.state_dict(),
                "model_config": model.config_dict(),
                "tokenizer_version": "ultron-bpe-v1",
                "tokenizer_json_sha256": hashlib.sha256(tokenizer_path.read_bytes()).hexdigest(),
                "parameter_count": model.parameter_count(),
                "training_steps": 2,
                "best_step": 1,
            }, checkpoint_path)
            result = generate_samples(str(checkpoint_path), ["Olá, ULTRON!"], tokenizer_json=str(tokenizer_path), max_new_tokens=4)
            self.assertEqual(result["tokenizer"], "ultron-bpe-v1")
            self.assertEqual(len(result["samples"]), 1)
            self.assertIn("checkpoint_sha256", result)
            self.assertTrue(result["experimental"])
            second_corpus = root / "second.txt"
            second_corpus.write_text(("Outro texto português para criar outro vocabulário.\n" * 3000), encoding="utf-8")
            second_tokenizer = root / "second-tokenizer.json"
            train_tokenizer(str(second_corpus), str(second_tokenizer), vocab_size=512)
            with self.assertRaises(ValueError):
                generate_samples(str(checkpoint_path), ["Olá"], tokenizer_json=str(second_tokenizer), max_new_tokens=4)


if __name__ == "__main__":
    unittest.main()
