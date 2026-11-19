from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

try:
    import torch
except ImportError:
    torch = None

if torch is not None:
    from backend.local_transformer_runtime import LocalTransformerRuntime, build_prompt
    from training.generative.model import ModelConfig, UltronTinyGPT
    from training.generative.tokenizer import TOKENIZER_VERSION


@unittest.skipIf(torch is None, "PyTorch is optional in the base CI")
class LocalTransformerRuntimeTests(unittest.TestCase):
    def test_prompt_includes_retrieved_memory_and_current_question(self):
        prompt = build_prompt(
            "Como continuo o projeto?",
            ["Decidimos manter o núcleo independente.", "Gemini é substituível."],
            ["Antes estávamos implementando memória."],
        )
        self.assertIn("núcleo independente", prompt)
        self.assertIn("Como continuo", prompt)
        self.assertLessEqual(len(prompt.encode("utf-8")), 120)

    def test_missing_checkpoint_fails_explicitly(self):
        with patch.dict(os.environ, {"ULTRON_GENERATIVE_CHECKPOINT": ""}):
            with self.assertRaisesRegex(RuntimeError, "ULTRON_GENERATIVE_CHECKPOINT"):
                LocalTransformerRuntime()

    def test_local_checkpoint_loads_and_generates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "tiny.pt")
            model = UltronTinyGPT(ModelConfig(context_length=128, width=16, layers=1, heads=1))
            torch.save({
                "model_state": model.state_dict(),
                "model_config": model.config_dict(),
                "tokenizer_version": TOKENIZER_VERSION,
            }, path)
            runtime = LocalTransformerRuntime(path)
            reply = runtime.generate("Explique o plano", ["O núcleo pertence ao ULTRON."], max_new_tokens=4)
            self.assertIsInstance(reply, str)
            self.assertTrue(reply)


if __name__ == "__main__":
    unittest.main()
