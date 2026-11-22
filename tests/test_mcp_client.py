import unittest
from unittest.mock import Mock
from mcp.client import MCPClient


class MCPClientTests(unittest.TestCase):
    def response(self, payload, session_id="session-123", status=200):
        response = Mock()
        response.status_code = status
        response.headers = {"Mcp-Session-Id": session_id, "Content-Type": "application/json"}
        response.json.return_value = payload
        response.text = ""
        response.raise_for_status.return_value = None
        return response

    def test_initialize_then_discover_tools_uses_same_session(self):
        client = MCPClient("https://mcp.example.test")
        client.session.post = Mock(side_effect=[
            self.response({"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-03-26"}}),
            self.response({}, status=202),
            self.response({"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "search"}]}}),
        ])
        tools = client.list_tools()
        self.assertEqual(tools[0]["name"], "search")
        self.assertEqual(client.session_id, "session-123")
        self.assertEqual(client.session.post.call_args_list[2].kwargs["headers"]["Mcp-Session-Id"], "session-123")

    def test_requires_https(self):
        with self.assertRaises(ValueError):
            MCPClient("http://insecure.example.test")


if __name__ == "__main__":
    unittest.main()
