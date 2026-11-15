import os
import tempfile
import unittest
from unittest.mock import patch

from backend import flywire_runtime
from backend.fly_brain import FlyBrainCore


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

    def test_chat_hook_is_off_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(FlyBrainCore._full_connectome_signal("quero açúcar"))

    def test_chat_hook_maps_only_documented_sensory_intents(self):
        expected = {"full_connectome_loaded": True, "active_neurons": 42, "neurons": 138639}
        with patch.dict(os.environ, {"ULTRON_ENABLE_FULL_FLYWIRE": "1"}):
            with patch("backend.flywire_runtime.simulate", return_value=expected) as simulate:
                self.assertEqual(FlyBrainCore._full_connectome_signal("quero comida"), expected)
                self.assertEqual(simulate.call_args.args, ("sugar", 0.01))
                self.assertIsNone(FlyBrainCore._full_connectome_signal("explique matemática"))

    def test_simulation_requires_real_data_and_never_falls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"ULTRON_FLYWIRE_ROOT": directory}):
                with self.assertRaisesRegex(RuntimeError, "Conectoma FlyWire não instalado"):
                    flywire_runtime.FlyWireRuntime()


if __name__ == "__main__":
    unittest.main()
