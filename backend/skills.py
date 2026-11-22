"""Built-in ULTRON skills. No third-party scripts are dynamically executed."""
from __future__ import annotations

from backend.agent_core import SELF_MODEL, improvement_proposal, plan_task
from backend.intent_model import predict_intent, resolve_intent, model_status
from backend.project_awareness import build_project_awareness
from backend.evolution_dispatch import dispatch_evolution_workflow

SKILLS = {
    "conversation": {"title": "Conversa", "intents": ["greeting", "thanks"], "risk": "low"},
    "help": {"title": "Ajuda e comandos", "intents": ["help"], "risk": "low"},
    "identity": {"title": "Autoconhecimento", "intents": ["identity"], "risk": "low"},
    "planner": {"title": "Planejador", "intents": ["plan"], "risk": "low"},
    "status": {"title": "Diagnóstico rápido", "intents": ["status"], "risk": "low"},
    "memory": {"title": "Memória protegida", "intents": ["remember"], "risk": "medium"},
    "self_review": {"title": "Autoavaliação", "intents": ["improve"], "risk": "low"},
    "safe_evolution": {"title": "Autoevolução segura", "intents": ["improve"], "risk": "review_required"},
    "recursive_evolution": {"title": "Autoevolução recursiva", "intents": ["improve"], "risk": "github_actions_dispatch"},
    "iphone_actions": {"title": "Ações seguras no iPhone", "intents": ["user_invoked_shortcut"], "risk": "permission_required"},
}

def list_skills() -> list[dict]:
    return [{"name": name, **details} for name, details in SKILLS.items()]

def _format_plan(goal: str) -> str:
    plan = plan_task(goal)
    lines = [f"Plano para: {plan['goal']}", f"Risco: {plan['risk']}",
             f"Aprovação humana: {'sim' if plan['human_approval_required'] else 'não'}"]
    lines.extend(f"{step['step']}. {step['action']}" for step in plan["steps"])
    return "\n".join(lines)

def run_intent_skill(message: str) -> str | None:
    prediction = resolve_intent(message)
    intent = prediction["intent"]
    if intent == "greeting":
        return "Oi! Sou o ULTRON. Meu núcleo leve está ativo; posso planejar, calcular, pesquisar e usar habilidades locais."
    if intent == "thanks":
        return "Por nada! Pode continuar. Vou priorizar respostas diretas e verificáveis."
    if intent == "help":
        return ("Habilidades ativas: conversa, planejamento, cálculo seguro, pesquisa web, "
                "diagnóstico, memória protegida, autoavaliação e proposta de autoevolução. "
                "Exemplos: /plan objetivo, /calc 12*(3+4), /research assunto, /self, /skills.")
    if intent == "identity":
        awareness = build_project_awareness()
        git = awareness["git"]
        counts = awareness["inventory"]["counts"]
        recent = git["recent_commits"][:3]
        history = "; ".join(
            f"{item['date']} {item['subject']}" for item in recent
        ) or "histórico Git indisponível neste ambiente"
        return (
            "Sou ULTRON. Meu autoconhecimento agora consulta o checkout real do projeto: "
            f"branch {git['branch'] or 'desconhecida'}, commit {git['head'] or 'indisponível'}, "
            f"{awareness['inventory']['total_files']} arquivos inventariados, "
            f"{counts['backend']} módulos backend, {counts['tests']} arquivos de teste e "
            f"{counts['swift']} arquivos Swift. Mudanças recentes: {history}. "
            "Meu classificador de intenções é próprio; o adaptador generativo é opcional. "
            "A presença de módulos no repositório não prova que estejam implantados no iPhone. "
            "Ainda não tenho um gerador autônomo geral de código."
        )
    if intent == "plan":
        return _format_plan(message)
    if intent == "status":
        status = model_status()
        return (f"ULTRON online no processo atual. Modelo {status['version']} carregado; "
                f"{status['training_examples']} exemplos de treino; {status['artifact_bytes']} bytes. "
                "Classificador de intenções ativo; geração livre de linguagem ainda não implementada.")
    if intent == "remember":
        return ("A memória pessoal ainda exige autenticação por instalação. Para não misturar "
                "dados entre usuários, esta conversa pública não grava memórias compartilhadas.")
    if intent == "improve":
        proposal = improvement_proposal(message)
        awareness = build_project_awareness()
        evolution = awareness["self_evolution"]
        return (
            "Diagnóstico da autoevolução com base no repositório atual: "
            f"benchmark congelado={'sim' if evolution['benchmark_available'] else 'não'}; "
            f"gate de regressões={'sim' if evolution['regression_and_improvement_gate_available'] else 'não'}; "
            f"workflow de avaliação de branches={'sim' if evolution['candidate_branch_evaluation_available'] else 'não'}; "
            f"geração autônoma de patches={'sim' if evolution['autonomous_code_candidate_generation'] else 'não'}; "
            f"pesquisa web para evolução={'sim' if evolution.get('web_research_for_evolution') else 'não'}; "
            f"revisão crítica={'sim' if evolution.get('critic_review_for_candidates') else 'não'}; "
            f"promoção no ramo de desenvolvimento={'sim' if evolution.get('automatic_merge_to_development') else 'não'}; "
            f"merge em produção={'sim' if evolution['automatic_merge_to_production'] else 'não'}. "
            "O worker pode gerar e testar mudanças em branches isoladas; a promoção ao núcleo de desenvolvimento depende do CI e da revisão crítica.\n"
            + "\n".join(f"- {item}" for item in proposal["plan"])
        )
    return None

def run_named_skill(name: str, input_text: str) -> dict:
    if name not in SKILLS:
        raise ValueError("Habilidade desconhecida.")
    if name == "recursive_evolution":
        try:
            result = dispatch_evolution_workflow(input_text)
            return {
                "skill": name,
                "response": "Ciclo de autoevolução enviado ao GitHub Actions. O worker vai pesquisar fontes públicas, inspecionar o checkout, propor uma mudança, executar testes e fazer uma revisão crítica antes de abrir/mesclar no ramo de desenvolvimento.",
                "execution": result,
                "model": predict_intent(input_text),
            }
        except (RuntimeError, ValueError) as exc:
            return {
                "skill": name,
                "response": str(exc),
                "execution": {"dispatched": False},
                "model": predict_intent(input_text),
            }
    if name == "iphone_actions":
        return {
            "skill": name,
            "response": (
                "Use o app Atalhos ou Siri para chamar Perguntar ao ULTRON. "
                "O app também pode copiar, ler e compartilhar respostas após toque. "
                "Ações em outros apps continuam limitadas pelas permissões públicas do iOS."
            ),
            "model": predict_intent(input_text),
            "execution_policy": "user_initiated_only",
        }
    response = run_intent_skill(input_text)
    if response is None:
        response = f"A habilidade {name} está instalada, mas a mensagem não corresponde a uma ação suportada."
    return {"skill": name, "response": response, "model": predict_intent(input_text)}
