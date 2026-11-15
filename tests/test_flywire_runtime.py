import os
import tempfile
import unittest
from unittest.mock import patch

from backend import flywire_runtime


class FlyWireRuntimeTests(unittest.TestCase):
    def test_status_is_explicit_when_connectome_is_not_installed(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"ULTRON_FLYWIRE_ROOT": directory}):
                result = flywire_runtime.status()
        self.assertFalse(result["available"])
        self.assertFalse(result["upstream_code_present"])
        self.assertEqual(result["connectome"], "FlyWire FAFB v783")
        self.assertEqual(len(result["missing_files"]), 2)

    def test_only_upstream_supported_stimuli_are_accepted(self):
        self.assertEqual(flywire_runtime._select_experiment("sugar"), "sugar")
        self.assertEqual(flywire_runtime._select_experiment("P9"), "p9")
        with self.assertRaises(ValueError):
            flywire_runtime._select_experiment("generic conversation")

    def test_simulation_requires_real_data_and_never_falls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"ULTRON_FLYWIRE_ROOT": directory}):
                with self.assertRaisesRegex(RuntimeError, "Conectoma FlyWire não instalado"):
                    flywire_runtime.FlyWireRuntime()


if __name__ == "__main__":
    unittest.main()
