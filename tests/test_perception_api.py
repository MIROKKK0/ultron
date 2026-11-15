import unittest
from fastapi.testclient import TestClient

from backend.app import app


class PerceptionApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_perception_endpoint_maps_only_supported_intents(self):
        feeding = self.client.post(
            "/brain/perception", json={"goal": "Quero comida"}
        )
        self.assertEqual(feeding.status_code, 200)
        self.assertEqual(feeding.json()["connectome_stimulus"], "sugar")

        locomotion = self.client.post(
            "/brain/perception", json={"goal": "Quero caminhar"}
        )
        self.assertEqual(locomotion.status_code, 200)
        self.assertEqual(locomotion.json()["connectome_stimulus"], "p9")

    def test_perception_endpoint_rejects_negated_and_mixed_intents(self):
        negated = self.client.post(
            "/brain/perception", json={"goal": "Não quero comida"}
        )
        self.assertEqual(negated.status_code, 200)
        self.assertFalse(negated.json()["connectome_mapped"])

        mixed = self.client.post(
            "/brain/perception", json={"goal": "Quero comer e caminhar"}
        )
        self.assertEqual(mixed.status_code, 200)
        self.assertEqual(mixed.json()["intent"], "ambiguous_multiple_supported_intents")
        self.assertIsNone(mixed.json()["connectome_stimulus"])

    def test_perception_endpoint_does_not_fake_language_mapping(self):
        response = self.client.post(
            "/brain/perception", json={"goal": "Explique cálculo diferencial"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["connectome_mapped"])
        self.assertIsNone(response.json()["connectome_stimulus"])


if __name__ == "__main__":
    unittest.main()
