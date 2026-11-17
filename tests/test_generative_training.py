import unittest

try:
    import torch
except ImportError:
    torch = None


@unittest.skipIf(torch is None, "PyTorch is installed only in the optional training workflow")
class GenerativeTrainingTests(unittest.TestCase):
    def test_vectorized_batches_have_next_token_alignment(self):
        from training.generative.train import sample_batch
        data = torch.arange(20, dtype=torch.long)
        inputs, targets = sample_batch(data, 3, 4, generator=torch.Generator().manual_seed(7))
        self.assertEqual(tuple(inputs.shape), (3, 4))
        self.assertTrue(torch.equal(targets, inputs + 1))

    def test_batch_sampling_is_reproducible(self):
        from training.generative.train import sample_batch
        data = torch.arange(100, dtype=torch.long)
        a = sample_batch(data, 4, 8, generator=torch.Generator().manual_seed(99))
        b = sample_batch(data, 4, 8, generator=torch.Generator().manual_seed(99))
        self.assertTrue(torch.equal(a[0], b[0]))
        self.assertTrue(torch.equal(a[1], b[1]))

    def test_split_keeps_validation_after_training_segment(self):
        from training.generative.train import split_corpus
        data = torch.arange(200, dtype=torch.long)
        train, validation = split_corpus(data, context_length=8, validation_fraction=0.2)
        self.assertEqual(int(train[-1]) + 1, int(validation[0]))
        self.assertLess(len(validation), len(data))

    def test_evaluation_restores_model_training_mode(self):
        from training.generative.model import ModelConfig, UltronTinyGPT
        from training.generative.train import evaluate_loss
        model = UltronTinyGPT(ModelConfig(context_length=8, width=16, layers=1, heads=2))
        model.train()
        data = torch.randint(0, 258, (80,))
        loss = evaluate_loss(model, data, batch_size=2, batches=2, context_length=8, seed=11)
        self.assertTrue(torch.isfinite(torch.tensor(loss)))
        self.assertTrue(model.training)


if __name__ == "__main__":
    unittest.main()
