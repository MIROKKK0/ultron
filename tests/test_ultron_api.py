import os
import tempfile
import threading
import unittest

import requests
from http.server import ThreadingHTTPServer
from ultron_api import UltronAPIHandler
from ultron_core import UltronCore


class UltronAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        UltronAPIHandler.core = UltronCore(os.path.join(self.temp.name, "api.db"))
        self.old_token = os.environ.get("ULTRON_API_TOKEN")
        os.environ["ULTRON_API_TOKEN"] = "test-token"
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), UltronAPIHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        if self.old_token is None:
            os.environ.pop("ULTRON_API_TOKEN", None)
        else:
            os.environ["ULTRON_API_TOKEN"] = self.old_token
        self.temp.cleanup()

    def test_private_graph_requires_token_and_syncs_per_installation(self):
        denied = requests.get(self.base + "/api/memory/graph?installation_id=device-a", timeout=3)
        self.assertEqual(denied.status_code, 401)
        headers = {"Authorization": "Bearer test-token"}
        synced = requests.post(
            self.base + "/api/memory/sync",
            headers=headers,
            json={"installation_id": "device-a", "replace": True,
                  "memories": [{"id": "m1", "content": "ULTRON memory node", "kind": "chat"}]},
            timeout=3,
        )
        self.assertEqual(synced.status_code, 200)
        graph = requests.get(
            self.base + "/api/memory/graph?installation_id=device-a",
            headers=headers,
            timeout=3,
        ).json()
        self.assertTrue(any(node["id"] == "device-a:m1" for node in graph["nodes"]))


if __name__ == "__main__":
    unittest.main()
