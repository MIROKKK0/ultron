"""Local deterministic language interface; not a pretrained LLM."""
from __future__ import annotations

import re
from typing import Iterable


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zà-ú0-9]{3,}", text.casefold()))


def decode_local(
    message: str,
    memories: Iterable[str] = (),
    history: Iterable[str] = (),
) -> str:
    text = message.strip()
    lower = text.casefold()
    strategy = "solver"
    memory_list = [str(item).strip() for item in memories if str(item).strip()]
    terms = _tokens(text)

    if re.search(r"\b(oi|olá|ola|e aí|eai|bom dia|boa tarde|boa noite)\b", lower):
        return (
            "Oi! Sou o ULTRON. A camada local está ativa. Posso conversar, organizar objetivos, "
            "planejar tarefas, calcular e consultar minhas memórias. Não uso "
            "tokens nem APIs de IA externas."
        )
    if lower in {"/help", "ajuda", "o que você faz?", "quem é você?", "quem e voce?", "o que você é?"}:
        return (
            "ULTRON — memória local, planejamento "
            "estruturado, cálculo seguro e reflexão. Comandos: /self, /plan objetivo, "
            "/remember nota, /calc expressão, /brain objetivo e /multi tarefa1 || tarefa2. "
            "O decodificador é local e determinístico; não é um LLM nem finge ser."
        )
    if lower.startswith("/self") or lower in {"quem é você", "quem e voce", "me fale sobre você", "me fale sobre voce"}:
        return (
            "Sou ULTRON. Minha arquitetura organiza tarefas com ferramentas locais; "
            "a camada linguística local converte a intenção em respostas estruturadas. "
            "Sem Gemini, OpenAI, Claude ou tokens externos. A camada linguística atual é determinística, não um LLM treinado."
        )
    if lower.startswith("/calc "):
        return "Use o mecanismo de cálculo seguro do ULTRON."
    if lower.startswith("/plan "):
        goal = text[6:].strip()
        if not goal:
            return "Informe o objetivo após /plan."
        return (
            f"Plano para: {goal}\n"
            f"Estratégia inicial: {strategy}.\n"
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
        return decode_local(text[7:].strip(), memory_list, history)
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
            f"Vou priorizar a estratégia {strategy}, com uma estratégia inicial.\n"
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
        return "Estou funcionando dentro dos recursos locais disponíveis. A camada local processa a entrada; posso ajudar com planejamento, cálculos e pesquisa quando a internet estiver disponível."
    if memory_list:
        query_matches = [
            item for item in memory_list
            if terms and len(terms & _tokens(item)) > 0
        ]
        if query_matches:
            return (
                "Recuperei estas memórias "
                "relacionadas:\n" + "\n".join(f"- {item}" for item in query_matches[:4]) +
                "\n\nPosso usar esse contexto para estruturar a próxima etapa."
            )
    return (
        "Recebi sua solicitação e processei a entrada pela camada local. "
        f"A atividade atual priorizou a estratégia **{strategy}**.\n\n"
        "Consigo executar localmente cálculos, comandos de memória e planos "
        "estruturados. Para responder conteúdo aberto com a profundidade de um "
        "grande modelo de linguagem, ainda falta um decodificador semântico local "
        "treinado; não vou simular inteligência que este circuito ainda não possui.\n"
        f"Solicitação registrada: {text[:1200]}"
    )
