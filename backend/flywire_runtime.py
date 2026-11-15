"""Optional, real FlyWire v783 simulator bridge.

This adapter loads the upstream eonsystemspbc/fly-brain PyTorch implementation
and its published connectome files. It never substitutes the 48-neuron demo
circuit when the full dataset is missing: callers receive an explicit error.
The FlyWire model is a sensory/motor neural simulator, not a text-generating LLM.
"""
from __future__ import annotations

import importlib
import importlib.util
import os
import sys
import threading
from pathlib import Path
from typing import Any

UPSTREAM = "https://github.com/eonsystemspbc/fly-brain"
EXPECTED_NEURONS = 138_639
SNAPSHOT_NEURONS = 139_255
UNMODELED_NEURONS = SNAPSHOT_NEURONS - EXPECTED_NEURONS
MODEL_COVERAGE_PERCENT = round(EXPECTED_NEURONS / SNAPSHOT_NEURONS * 100.0, 2)
DATA_FILES = (
    Path("data/2025_Completeness_783.csv"),
    Path("data/2025_Connectivity_783.parquet"),
)
_lock = threading.RLock()
_runtime: "FlyWireRuntime | None" = None


def _root() -> Path:
    return Path(os.getenv("ULTRON_FLYWIRE_ROOT", "vendor/fly-brain")).expanduser()


def _memory_budget() -> dict[str, Any]:
    """Estimate safe memory headroom before importing PyTorch or allocating weights."""
    required_mib = max(1024, int(os.getenv("ULTRON_FLYWIRE_MIN_FREE_MIB", "6144")))
    available_bytes: int | None = None
    source = "unknown"
    # Respect container limits first; host MemAvailable can be misleading in Docker.
    for limit_path, current_path in (
        (Path("/sys/fs/cgroup/memory.max"), Path("/sys/fs/cgroup/memory.current")),
        (Path("/sys/fs/cgroup/memory/memory.limit_in_bytes"),
         Path("/sys/fs/cgroup/memory/memory.usage_in_bytes")),
    ):
        try:
            limit_raw = limit_path.read_text().strip()
            current_raw = current_path.read_text().strip()
            if limit_raw != "max":
                limit = int(limit_raw)
                current = int(current_raw)
                if 0 < limit < (1 << 60):
                    available_bytes = max(0, limit - current)
                    source = "cgroup"
                    break
        except (OSError, ValueError):
            continue
    if available_bytes is None:
        try:
            for line in Path("/proc/meminfo").read_text().splitlines():
                if line.startswith("MemAvailable:"):
                    available_bytes = int(line.split()[1]) * 1024
                    source = "memavailable"
                    break
        except (OSError, ValueError, IndexError):
            pass
    available_mib = round(available_bytes / (1024 * 1024), 1) if available_bytes is not None else None
    return {
        "available_mib": available_mib,
        "required_free_mib": required_mib,
        "source": source,
        "ready": available_mib is not None and available_mib >= required_mib,
    }


def status() -> dict[str, Any]:
    root = _root()
    missing = [str(path) for path in DATA_FILES if not (root / path).is_file()]
    code_files = (root / "code" / "benchmark.py", root / "code" / "run_pytorch.py")
    missing_code = [str(path.relative_to(root)) for path in code_files if not path.is_file()]
    code_ready = not missing_code
    dependencies = {name: importlib.util.find_spec(name) is not None for name in ("torch", "pandas", "pyarrow", "numpy")}
    missing_dependencies = [name for name, present in dependencies.items() if not present]
    return {
        "available": not missing and code_ready and not missing_dependencies,
        "connectome": "FlyWire FAFB v783",
        "expected_neurons": EXPECTED_NEURONS,
        "snapshot_neurons": SNAPSHOT_NEURONS,
        "modeled_neurons": EXPECTED_NEURONS,
        "unmodeled_snapshot_neurons": UNMODELED_NEURONS,
        "model_coverage_percent": MODEL_COVERAGE_PERCENT,
        "upstream": UPSTREAM,
        "root": str(root),
        "missing_files": missing,
        "upstream_code_present": code_ready,
        "missing_code_files": missing_code,
        "dependencies": dependencies,
        "missing_dependencies": missing_dependencies,
        "backend": "PyTorch CPU",
        "memory_budget": _memory_budget(),
        "license_note": "Upstream code GPL-2.0-or-later; FlyWire-derived data terms must be preserved.",
    }


def _select_experiment(stimulus: str) -> str:
    value = stimulus.strip().casefold()
    if value not in {"sugar", "p9"}:
        raise ValueError("Estímulo permitido: sugar ou p9.")
    return value


class FlyWireRuntime:
    """Persistent CPU session using the upstream sparse whole-brain model."""

    def __init__(self) -> None:
        budget = _memory_budget()
        if not budget["ready"]:
            raise RuntimeError(
                "Memória insuficiente para carregar o conectoma FlyWire com segurança: "
                f"{budget['available_mib']} MiB disponíveis; "
                f"{budget['required_free_mib']} MiB livres exigidos. "
                "Use um host com mais RAM ou mantenha o modo leve."
            )
        self.root = _root().resolve()
        missing = [str(path) for path in DATA_FILES if not (self.root / path).is_file()]
        if missing or not (self.root / "code" / "run_pytorch.py").is_file():
            raise RuntimeError(
                "Conectoma FlyWire não instalado. Execute scripts/bootstrap_flywire.sh; "
                f"arquivos ausentes: {', '.join(missing) or 'code/run_pytorch.py'}"
            )

        os.environ["FLY_BRAIN_DISABLE_SPIKE_IO"] = "1"
        code_dir = str(self.root / "code")
        if code_dir not in sys.path:
            sys.path.insert(0, code_dir)

        try:
            importlib.invalidate_caches()
            benchmark = importlib.import_module("benchmark")
            runner = importlib.import_module("run_pytorch")
            import torch
        except Exception as exc:
            raise RuntimeError(
                "Dependências do simulador FlyWire ausentes. Instale requirements-flywire.txt."
            ) from exc

        self.torch = torch
        self.runner = runner
        self.benchmark = benchmark
        self.device = torch.device("cpu")
        threads = max(1, min(4, int(os.getenv("ULTRON_FLYWIRE_THREADS", "2"))))
        torch.set_num_threads(threads)
        self.flyid_to_index, _ = runner.get_hash_tables(str(benchmark.path_comp))
        self.weights = runner.get_weights(
            str(benchmark.path_con), str(benchmark.path_comp), str(benchmark.path_wt), csr=True
        ).to(device=self.device)
        self.neuron_count = int(self.weights.shape[0])
        if self.neuron_count < 130_000:
            raise RuntimeError(
                f"Conectoma incompleto: {self.neuron_count} neurônios; esperado aproximadamente {EXPECTED_NEURONS}."
            )
        self.experiments = {}
        self.sessions = {}

    def simulate(self, stimulus: str, duration_sec: float = 0.1) -> dict[str, Any]:
        key = _select_experiment(stimulus)
        if not 0.01 <= float(duration_sec) <= 0.1:
            raise ValueError("A duração por chamada deve ficar entre 0,01 e 0,1 segundo.")
        experiment = self.benchmark.get_experiment(key)
        if key not in self.sessions:
            exc_indices = [self.flyid_to_index[n] for n in experiment["neu_exc"]]
            model = self.runner.TorchModel(
                1, self.neuron_count, self.runner.DT, self.runner.MODEL_PARAMS,
                self.weights, exc_indices=exc_indices, device=str(self.device),
            )
            state = model.state_init()
            rates = self.torch.zeros((1, self.neuron_count), device=self.device)
            rates[:, exc_indices] = float(experiment["stim_rate"])
            generator = self.torch.Generator(device="cpu").manual_seed(783)
            self.sessions[key] = (model, state, rates, generator)

        model, state, rates, generator = self.sessions[key]
        steps = int(float(duration_sec) * 1000.0 / float(self.runner.DT))
        total_spikes = 0
        active_neurons: set[int] = set()
        with self.torch.no_grad():
            for _ in range(steps):
                state = model(*((rates,) + tuple(state)), generator=generator)
                spikes = state[2]
                total_spikes += int(spikes.sum().item())
                if bool(spikes.any()):
                    active_neurons.update(
                        int(index) for index in spikes[0].nonzero(as_tuple=False).flatten().tolist()
                    )
        self.sessions[key] = (model, state, rates, generator)
        return {
            "engine": "upstream_flywire_pytorch",
            "connectome": "FlyWire FAFB v783",
            "full_connectome_loaded": True,
            "neurons": self.neuron_count,
            "stimulus": key,
            "stimulus_name": experiment["name"],
            "simulation_seconds": float(duration_sec),
            "timestep_ms": float(self.runner.DT),
            "steps": steps,
            "active_neurons": len(active_neurons),
            "spikes": total_spikes,
            "device": "cpu",
            "language_generation": False,
            "interpretation": (
                "Atividade neural simulada do conectoma; não é uma resposta linguística "
                "nem prova de raciocínio geral."
            ),
        }


def simulate(stimulus: str, duration_sec: float = 0.1) -> dict[str, Any]:
    global _runtime
    with _lock:
        if _runtime is None:
            _runtime = FlyWireRuntime()
        return _runtime.simulate(stimulus, duration_sec)


def runtime_loaded() -> bool:
    """True only after the real connectome and model are resident in this process."""
    return _runtime is not None
