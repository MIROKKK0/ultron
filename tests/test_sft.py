import json, tempfile, unittest
from pathlib import Path
try:
    import torch
except ImportError:
    torch = None

@unittest.skipIf(torch is None, "PyTorch is installed only in the optional training workflow")
class SFTDataTests(unittest.TestCase):
    def test_only_completion_tokens_are_supervised(self):
        from training.generative.sft import load_pairs
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pairs.jsonl"
            path.write_text(json.dumps({"split":"train","prompt":"Pergunta","completion":"Resposta"}, ensure_ascii=False)+"\\n", encoding="utf-8")
            inputs, labels = load_pairs(str(path), "train", 128)[0]
            self.assertEqual(inputs.ndim, 1)
            self.assertTrue((labels == -100).any())
            self.assertTrue((labels != -100).any())

    def test_empty_split_is_rejected(self):
        from training.generative.sft import load_pairs
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pairs.jsonl"
            path.write_text(json.dumps({"split":"train","prompt":"Q","completion":"A"})+"\\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_pairs(str(path), "eval", 128)

if __name__ == "__main__":
    unittest.main()
