import unittest
try:
    import torch
except ImportError:
    torch = None

@unittest.skipIf(torch is None, "PyTorch is installed only in the optional training workflow")
class TinyTransformerTests(unittest.TestCase):
    def test_forward_loss_backward_and_greedy_generation(self):
        from training.generative.model import ModelConfig, UltronTinyGPT
        from training.generative.tokenizer import BOS_ID
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
        from training.generative.model import ModelConfig, UltronTinyGPT
        model = UltronTinyGPT(ModelConfig(context_length=8, width=32, layers=1, heads=4))
        with self.assertRaises(ValueError):
            model(torch.ones((1, 9), dtype=torch.long))

    def test_attention_is_causal(self):
        from training.generative.model import ModelConfig, UltronTinyGPT
        torch.manual_seed(4)
        model = UltronTinyGPT(ModelConfig(context_length=16, width=32, layers=1, heads=4))
        model.eval()
        a = torch.tensor([[10, 11, 12, 13, 14, 15]])
        b = torch.tensor([[10, 11, 12, 13, 99, 98]])
        logits_a, _ = model(a)
        logits_b, _ = model(b)
        self.assertTrue(torch.allclose(logits_a[:, :4], logits_b[:, :4], atol=1e-6))

    def test_generate_restores_training_mode(self):
        from training.generative.model import ModelConfig, UltronTinyGPT
        model = UltronTinyGPT(ModelConfig(context_length=16, width=32, layers=1, heads=4))
        model.train()
        model.generate(torch.tensor([[1, 2]]), max_new_tokens=1)
        self.assertTrue(model.training)

    def test_sampling_generation_is_reproducible_with_seeded_generator(self):
        from training.generative.model import ModelConfig, UltronTinyGPT
        model = UltronTinyGPT(ModelConfig(context_length=16, width=32, layers=1, heads=4))
        seed_a = torch.Generator().manual_seed(123)
        seed_b = torch.Generator().manual_seed(123)
        prompt = torch.tensor([[1, 2, 3]])
        first = model.generate(prompt.clone(), max_new_tokens=5, temperature=0.8, top_k=12, generator=seed_a)
        second = model.generate(prompt.clone(), max_new_tokens=5, temperature=0.8, top_k=12, generator=seed_b)
        self.assertTrue(torch.equal(first, second))

    def test_generation_rejects_invalid_sampling_parameters(self):
        from training.generative.model import ModelConfig, UltronTinyGPT
        model = UltronTinyGPT(ModelConfig(context_length=16, width=32, layers=1, heads=4))
        with self.assertRaises(ValueError):
            model.generate(torch.tensor([[1]]), temperature=-1)
        with self.assertRaises(ValueError):
            model.generate(torch.tensor([[1]]), temperature=1, top_k=0)

    def test_rejects_mismatched_targets(self):
        from training.generative.model import ModelConfig, UltronTinyGPT
        model = UltronTinyGPT(ModelConfig(context_length=16, width=32, layers=1, heads=4))
        with self.assertRaises(ValueError):
            model(torch.ones((1, 4), dtype=torch.long), torch.ones((1, 3), dtype=torch.long))

if __name__ == "__main__":
    unittest.main()
