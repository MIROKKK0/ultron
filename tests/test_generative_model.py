import unittest

import torch

from training.generative.model import ModelConfig, UltronTinyGPT
from training.generative.tokenizer import BOS_ID


class TinyTransformerTests(unittest.TestCase):
    def test_forward_loss_backward_and_greedy_generation(self):
        config = ModelConfig(context_length=16, width=32, layers=1, heads=4)
        model = UltronTinyGPT(config)
        inputs = torch.randint(0, config.vocab_size, (2, 8))
        targets = torch.randint(0, config.vocab_size, (2, 8))
        logits, loss = model(inputs, targets)
        self.assertEqual(tuple(logits.shape), (2, 8, config.vocab_size))
        self.assertIsNotNone(loss)
        loss.backward()
        generated = model.generate(torch.tensor([[BOS_ID, 97]]), max_new_tokens=2)
        self.assertEqual(tuple(generated.shape), (1, 4))
        self.assertGreater(model.parameter_count(), 0)

    def test_rejects_input_longer_than_context(self):
        model = UltronTinyGPT(ModelConfig(context_length=8, width=32, layers=1, heads=4))
        with self.assertRaises(ValueError):
            model(torch.ones((1, 9), dtype=torch.long))


if __name__ == "__main__":
    unittest.main()
