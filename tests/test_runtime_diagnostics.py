import unittest

from backend.runtime_diagnostics import memory_snapshot, parse_rss_bytes


class RuntimeDiagnosticsTests(unittest.TestCase):
    def test_parses_linux_resident_memory(self):
        self.assertEqual(parse_rss_bytes("Name:\tpython\nVmRSS:\t1234 kB\n"), 1234 * 1024)

    def test_missing_rss_is_unknown(self):
        self.assertIsNone(parse_rss_bytes("Name:\tpython\nVmSize:\t100 kB\n"))

    def test_budget_is_clamped(self):
        self.assertEqual(memory_snapshot(1)["budget_mb"], 64)


if __name__ == "__main__":
    unittest.main()
