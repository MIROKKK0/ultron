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

    def test_status_reports_exact_upstream_code_license(self):
        result = flywire_runtime.status()
        self.assertIn("GPL-2.0-only", result["license_note"])
        self.assertNotIn("or-later", result["license_note"])

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

    def test_full_connectome_activity_enters_neural_control_state(self):
        simulated = {
            "full_connectome_loaded": True,
            "active_neurons": 1200,
            "neurons": 138639,
            "spikes": 3400,
            "stimulus": "sugar",
        }
        core = FlyBrainCore()
        with patch.dict(os.environ, {"ULTRON_ENABLE_FULL_FLYWIRE": "1"}):
            with patch("backend.flywire_runtime.simulate", return_value=simulated):
                state = core.process("quero comida")
        self.assertTrue(state["is_full_connectome"])
        self.assertEqual(state["core"], "flywire_v783_with_local_control_circuit")
        self.assertEqual(state["neurons"], 138639)
        self.assertEqual(state["full_connectome"]["spikes"], 3400)

    def test_full_mode_fails_closed_when_connectome_is_unavailable(self):
        with patch.dict(os.environ, {"ULTRON_ENABLE_FULL_FLYWIRE": "1"}):
            with patch("backend.flywire_runtime.simulate", side_effect=RuntimeError("missing connectome")):
                with self.assertRaisesRegex(RuntimeError, "missing connectome"):
                    FlyBrainCore._full_connectome_signal("quero comida")

    def test_simulation_requires_real_data_and_never_falls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"ULTRON_FLYWIRE_ROOT": directory}):
                with self.assertRaisesRegex(RuntimeError, "Conectoma FlyWire não instalado"):
                    flywire_runtime.FlyWireRuntime()


if __name__ == "__main__":
    unittest.main()
