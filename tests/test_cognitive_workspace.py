import unittest

from backend.cognitive_workspace import CognitiveWorkspace


class CognitiveWorkspaceTests(unittest.TestCase):
    def test_capacity_evicts_lowest_salience(self):
        workspace = CognitiveWorkspace(capacity=2)
        workspace.publish("goal", "objetivo", source="user", priority=1.0)
        workspace.publish("noise", "detalhe irrelevante", source="tool", priority=0.1)
        workspace.publish("evidence", "evidência central", source="research", priority=0.9)
        contents = [item["content"] for item in workspace.snapshot()["attention"]]
        self.assertIn("objetivo", contents)
        self.assertIn("evidência central", contents)
        self.assertNotIn("detalhe irrelevante", contents)

    def test_attention_prefers_confident_and_important_items(self):
        workspace = CognitiveWorkspace()
        workspace.publish("guess", "hipótese", source="model", confidence=0.2, priority=1.0)
        workspace.publish("fact", "fato com fonte", source="verified_source", confidence=0.95, priority=0.9)
        self.assertEqual(workspace.attend(1)[0].kind, "fact")

    def test_workspace_rejects_invalid_scores_and_empty_content(self):
        workspace = CognitiveWorkspace()
        with self.assertRaises(ValueError):
            workspace.publish("goal", "x", source="user", confidence=1.1)
        with self.assertRaises(ValueError):
            workspace.publish("goal", " ", source="user")

    def test_snapshot_is_explicitly_per_request(self):
        workspace = CognitiveWorkspace()
        workspace.publish("goal", "analisar o problema", source="user")
        self.assertIn("per_request_only", workspace.snapshot()["policy"])


if __name__ == "__main__":
    unittest.main()
