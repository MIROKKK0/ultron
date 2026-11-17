"""Built-in ULTRON skills. No third-party scripts are dynamically executed."""
from __future__ import annotations

from backend.agent_core import SELF_MODEL, improvement_proposal, plan_task
from backend.intent_model import predict_intent, model_status

SKILLS = {
    "conversation": {"title": "Conversa", "intents": ["greeting", "thanks"], "risk": "low"},
    "help": {"title": "Ajuda e comandos", "intents": ["help"], "risk": "low"},
    "identity": {"title": "Autoconhecimento", "intents": ["identity"], "risk": "low"},
    "planner": {"title": "Planejador", "intents": ["plan"], "risk": "low"},
    "status": {"title": "Diagnóstico rápido", "intents": ["status"], "risk": "low"},
    "memory": {"title": "Memória protegida", "intents": ["remember"], "risk": "medium"},
    "self_review": {"title": "Autoavaliação", "intents": ["improve"], "risk": "low"},
    "safe_evolution": {"title": "Autoevolução segura", "intents": ["improve"], "risk": "review_required"},
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
    prediction = predict_intent(message)
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
        return ("Sou ULTRON. Minha versão atual usa um classificador próprio treinado do zero "
                "para reconhecer intenções e acionar ferramentas locais. Ainda não sou um LLM "
                "generativo geral e não uso modelos ou provedores de IA externos.")
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
        return ("Autoavaliação concluída: posso propor melhorias, comparar métricas, criar testes "
                "e preparar uma branch/PR. Não altero produção, segurança ou pesos automaticamente.\n"
                + "\n".join(f"- {item}" for item in proposal["plan"]))
    return None

def run_named_skill(name: str, input_text: str) -> dict:
    if name not in SKILLS:
        raise ValueError("Habilidade desconhecida.")
    response = run_intent_skill(input_text)
    if response is None:
        response = f"A habilidade {name} está instalada, mas a mensagem não corresponde a uma ação suportada."
    return {"skill": name, "response": response, "model": predict_intent(input_text)}
