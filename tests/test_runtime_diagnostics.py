import unittest

from backend.runtime_diagnostics import memory_snapshot, parse_rss_bytes


class RuntimeDiagnosticsTests(unittest.TestCase):
    def test_parses_linux_resident_memory(self):
        self.assertEqual(parse_rss_bytes("Name:\tpython\nVmRSS:\t1234 kB\n"), 1234 * 1024)

    def test_missing_rss_is_reported_as_unknown(self):
        self.assertIsNone(parse_rss_bytes("Name:\tpython\nVmSize:\t100 kB\n"))

    def test_memory_budget_is_clamped_and_pressure_is_bounded(self):
        snapshot = memory_snapshot(1)
        self.assertEqual(snapshot["budget_mb"], 64)
        self.assertIn(snapshot["pressure"], {"normal", "high", "critical", "unknown"})


if __name__ == "__main__":
    unittest.main()
