"""Long-running background worker for ULTRON's persistent SQLite task queue."""
from __future__ import annotations

import argparse
import os
import signal
import time
from pathlib import Path

from openai import OpenAI
from ultron_core import UltronCore, SPECIALISTS

SYSTEM = """Você é um especialista executor do ULTRON. Execute somente o objetivo da tarefa,
explique evidências e limitações, não alegue ações externas que não realizou e devolva
um resultado verificável. Preserve a identidade e memória do núcleo ULTRON."""


def run_worker(once: bool = False, max_runtime: int = 0, idle_sleep: float = 5.0) -> None:
    api_key = os.getenv("ULTRON_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Configure ULTRON_LLM_API_KEY no ambiente do worker.")
    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("ULTRON_LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1",
    )
    model = os.getenv("ULTRON_LLM_MODEL") or os.getenv("ULTRON_MODEL") or "gpt-4o-mini"
    core = UltronCore()
    started = time.monotonic()
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    core.event("worker.started", {"model": model, "pid": os.getpid()})

    while not stopping:
        if max_runtime and time.monotonic() - started >= max_runtime:
            break
        task = core.next_task()
        if task is None:
            if once:
                break
            time.sleep(max(1.0, idle_sleep))
            continue
        try:
            specialist = SPECIALISTS.get(task.specialist, SPECIALISTS["architect"])
            response = client.chat.completions.create(
                model=model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": SYSTEM + "\nEspecialidade: " + specialist},
                    {"role": "user", "content": task.objective},
                ],
            )
            result = response.choices[0].message.content or "O modelo não retornou conteúdo."
            core.finish_task(task.id, result, "needs_review")
            core.event("worker.task_completed", {"task_id": task.id, "specialist": task.specialist})
        except Exception as exc:
            core.finish_task(task.id, str(exc), "failed")
            core.event("worker.task_failed", {"task_id": task.id, "error_type": type(exc).__name__})
        if once:
            break
    core.event("worker.stopped", {"processed_until": core._now()})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ULTRON background task worker")
    parser.add_argument("--once", action="store_true", help="Processa no máximo uma tarefa e encerra")
    parser.add_argument("--max-runtime", type=int, default=0, help="Tempo máximo em segundos; 0 = contínuo")
    parser.add_argument("--idle-sleep", type=float, default=5.0)
    args = parser.parse_args()
    run_worker(args.once, args.max_runtime, args.idle_sleep)
