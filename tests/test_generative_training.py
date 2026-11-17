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

    def test_training_saves_best_validation_checkpoint_and_test_metric(self):
        import argparse
        import tempfile
        from pathlib import Path
        from training.generative.train import train
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = ("A história do Brasil tem muitas cidades e pessoas. " * 500)
            validation = ("O Brasil possui rios, florestas e cidades. " * 120)
            test = ("A língua portuguesa é falada em vários países. " * 120)
            (root / "train.txt").write_text(corpus, encoding="utf-8")
            (root / "validation.txt").write_text(validation, encoding="utf-8")
            (root / "test.txt").write_text(test, encoding="utf-8")
            args = argparse.Namespace(
                steps=3, batch_size=2, eval_batches=1, eval_interval=1, threads=1,
                warmup_steps=1, min_lr_ratio=0.1, seed=17, corpus=str(root / "train.txt"),
                validation_corpus=str(root / "validation.txt"), test_corpus=str(root / "test.txt"),
                context_length=16, validation_fraction=0.1, width=16, layers=1, heads=2,
                learning_rate=3e-4, early_stopping_patience=0, min_delta=0.0,
                output=str(root / "checkpoint.pt"),
            )
            result = train(args)
            checkpoint = torch.load(root / "checkpoint.pt", map_location="cpu", weights_only=True)
            self.assertEqual(result["training_steps"], 3)
            self.assertGreaterEqual(checkpoint["best_step"], 1)
            self.assertIsNotNone(checkpoint["test_loss"])

            args.init_checkpoint = str(root / "checkpoint.pt")
            args.output = str(root / "checkpoint-next.pt")
            args.steps = 2
            continued = train(args)
            next_checkpoint = torch.load(root / "checkpoint-next.pt", map_location="cpu", weights_only=True)
            self.assertTrue(continued["initialized_from_checkpoint"])
            self.assertEqual(next_checkpoint["cumulative_training_steps"], 5)
            self.assertIsNotNone(next_checkpoint["parent_checkpoint_sha256"])

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
