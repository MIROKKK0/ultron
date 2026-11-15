"""Local semantic decoder controlled by ULTRON's mandatory neural core.

This is a deterministic, token-free language interface, not a pretrained LLM.
The FlyBrain state selects the response strategy; no cloud provider is called.
"""
from __future__ import annotations

import re
from typing import Iterable


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zà-ú0-9]{3,}", text.casefold()))


def decode_local(
    message: str,
    memories: Iterable[str] = (),
    history: Iterable[str] = (),
    neural_state: dict | None = None,
) -> str:
    text = message.strip()
    lower = text.casefold()
    state = neural_state or {}
    scores = state.get("role_scores", {})
    # Neural activity controls which cognitive strategy gets priority.
    strategy = max(
        ("planner", "solver", "critic"),
        key=lambda role: float(scores.get(role, 0.0)),
        default="solver",
    )
    memory_list = [str(item).strip() for item in memories if str(item).strip()]
    terms = _tokens(text)

    if re.search(r"\b(oi|olá|ola|e aí|eai|bom dia|boa tarde|boa noite)\b", lower):
        return (
            "Oi! Sou o ULTRON. Meu núcleo neural local está ativo e controla "
            "a prioridade desta resposta. Posso conversar, organizar objetivos, "
            "planejar tarefas, calcular e consultar minhas memórias. Não uso "
            "tokens nem APIs de IA externas."
        )
    if lower in {"/help", "ajuda", "o que você faz?", "quem é você?", "quem e voce?", "o que você é?"}:
        return (
            "ULTRON — núcleo FlyBrain obrigatório, memória local, planejamento "
            "estruturado, cálculo seguro e reflexão. Comandos: /self, /plan objetivo, "
            "/remember nota, /calc expressão, /brain objetivo e /multi tarefa1 || tarefa2. "
            "O decodificador é local e determinístico; não é um LLM nem finge ser."
        )
    if lower.startswith("/self") or lower in {"quem é você", "quem e voce", "me fale sobre você", "me fale sobre voce"}:
        return (
            "Sou ULTRON. O núcleo neural FlyBrain controla atenção e prioridade; "
            "a camada linguística local converte a intenção em respostas estruturadas. "
            "Sem Gemini, OpenAI, Claude ou tokens externos. O circuito atual é um "
            "microcircuito LIF de 48 neurônios, não o conectoma FlyWire completo."
        )
    if lower.startswith("/calc "):
        return "Use o mecanismo de cálculo seguro do ULTRON."
    if lower.startswith("/plan "):
        goal = text[6:].strip()
        if not goal:
            return "Informe o objetivo após /plan."
        return (
            f"Plano neural para: {goal}\n"
            f"Estratégia priorizada pelo cérebro: {strategy}.\n"
            "1. Definir o resultado observável.\n"
            "2. Dividir em etapas pequenas e reversíveis.\n"
            "3. Identificar dependências e riscos.\n"
            "4. Executar cada etapa com ferramentas autorizadas.\n"
            "5. Validar com testes e evidências.\n"
            "6. Registrar o resultado e aprender com o feedback."
        )
    if lower.startswith("/remember "):
        return "Use /remember texto para gravar uma memória persistente."
    if lower.startswith("/brain "):
        return decode_local(text[7:].strip(), memory_list, history, state)
    if lower.startswith("/multi "):
        tasks = [part.strip() for part in text[7:].split("||") if part.strip()]
        if not tasks:
            return "Informe tarefas separadas por ||."
        return "\n".join(
            f"{index}. {task}\n   Próxima ação: definir critério de conclusão e validar."
            for index, task in enumerate(tasks, 1)
        )
    if any(word in lower for word in ("quem sou", "minhas memórias", "o que lembra")):
        if not memory_list:
            return "Ainda não encontrei memórias relevantes para essa solicitação."
        return "Memórias relevantes:\n" + "\n".join(f"- {item}" for item in memory_list[:5])

    if any(word in lower for word in ("plano", "planeje", "organize", "como faço", "como fazer", "etapas", "me ajuda a planejar", "quero planejar")):
        return (
            f"Vou priorizar a estratégia {strategy}, conforme a atividade neural.\n"
            f"Objetivo identificado: {text}\n"
            "1. Esclarecer o resultado esperado.\n"
            "2. Separar o trabalho em etapas verificáveis.\n"
            "3. Começar pela etapa de menor risco.\n"
            "4. Testar o resultado antes de avançar.\n"
            "5. Guardar aprendizados úteis na memória."
        )
    if any(word in lower for word in ("obrigado", "obrigada", "valeu", "agradeço", "agradeco")):
        return "Por nada! Estou aqui. Pode continuar falando comigo normalmente, sem comandos especiais."
    if any(word in lower for word in ("tudo bem", "como você está", "como voce esta")):
        return "Estou funcionando dentro dos recursos locais disponíveis. Meu núcleo FlyBrain processa a entrada; posso ajudar com planejamento, cálculos e pesquisa quando a internet estiver disponível."
    if memory_list:
        query_matches = [
            item for item in memory_list
            if terms and len(terms & _tokens(item)) > 0
        ]
        if query_matches:
            return (
                "Considerei a atividade do núcleo neural e recuperei estas memórias "
                "relacionadas:\n" + "\n".join(f"- {item}" for item in query_matches[:4]) +
                "\n\nPosso usar esse contexto para estruturar a próxima etapa."
            )
    return (
        "Ainda não consegui interpretar essa pergunta com o decodificador local. "
        "Tente reformular ou ative o Qwen nas configurações para respostas abertas. "
        f"Estratégia neural priorizada: {strategy}."
    )
