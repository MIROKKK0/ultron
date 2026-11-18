"""Small deterministic hierarchical planner with explicit outcome simulation."""
from __future__ import annotations
import re

def plan_hierarchical(goal: str) -> dict:
    goal = " ".join(str(goal).split())
    if not goal or len(goal) > 4000:
        raise ValueError("Objetivo inválido.")
    parts = [p.strip(" ,;") for p in re.split(r"\s+(?:e depois|depois|então|além disso)\s+|[;]", goal, flags=re.I) if p.strip(" ,;")]
    subtasks = []
    for i, part in enumerate(parts[:8], 1):
        subtasks.append({"id": f"T{i}", "goal": part[:500], "depends_on": [f"T{i-1}"] if i > 1 else [],
                         "success_check": "resultado observável e verificável"})
    if not subtasks:
        subtasks = [{"id": "T1", "goal": goal, "depends_on": [], "success_check": "resultado observável e verificável"}]
    risk_words = ("apagar", "excluir", "comprar", "pagar", "publicar", "enviar", "deploy", "implantar")
    risky = any(w in goal.casefold() for w in risk_words)
    scenarios = [
        {"name": "success", "assumption": "ferramentas disponíveis e entradas válidas", "outcome": "validar cada subresultado e concluir"},
        {"name": "partial_failure", "assumption": "uma etapa falha ou retorna resultado incompleto", "outcome": "preservar etapas concluídas, registrar falha e tentar recuperação segura"},
        {"name": "blocked", "assumption": "falta permissão, credencial ou confirmação", "outcome": "parar antes da ação protegida e solicitar autorização"},
    ]
    return {"goal": goal, "level": "hierarchical", "subtasks": subtasks,
            "dependencies": [{"before": f"T{i-1}", "after": f"T{i}"} for i in range(2, len(subtasks)+1)],
            "simulated_outcomes": scenarios, "risk": "high" if risky else "low",
            "human_approval_required": risky,
            "note": "Simulações são cenários heurísticos, não previsões probabilísticas."}
