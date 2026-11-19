import os
import tempfile
import unittest
from pathlib import Path

try:
    import torch
except ImportError:
    torch = None


@unittest.skipIf(torch is None, "PyTorch is installed only in the optional model workflow")
class LocalNeuralEncoderTests(unittest.TestCase):
    def test_checkpoint_round_trip_is_deterministic_and_dense(self):
        from training.generative.model import ModelConfig, UltronTinyGPT
        from training.generative.tokenizer import TOKENIZER_VERSION
        from backend.local_neural_encoder import LocalNeuralEncoder

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tiny.pt"
            config = ModelConfig(context_length=64, width=32, layers=1, heads=4)
            torch.manual_seed(23)
            model = UltronTinyGPT(config)
            torch.save({
                "model_config": model.config_dict(),
                "model_state": model.state_dict(),
                "tokenizer_version": TOKENIZER_VERSION,
            }, path)
            encoder = LocalNeuralEncoder(path)
            first = encoder.encode("O ULTRON guarda experiências localmente.")
            second = encoder.encode("O ULTRON guarda experiências localmente.")
            self.assertEqual(first, second)
            self.assertEqual(len(first), config.width)
            self.assertAlmostEqual(sum(v * v for v in first.values()), 1.0, places=5)
            self.assertTrue(encoder.VERSION.startswith("ultron-tiny-mean-v1:"))

    def test_missing_checkpoint_fails_closed(self):
        from backend.local_neural_encoder import LocalNeuralEncoder
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                LocalNeuralEncoder(Path(directory) / "missing.pt")


if __name__ == "__main__":
    unittest.main()
