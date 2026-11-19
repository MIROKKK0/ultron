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
            "ULTRON — classificador próprio de intenções, planejamento, cálculo seguro, pesquisa web e habilidades locais. Comandos: /self, /plan objetivo, /remember nota, /calc expressão, /brain objetivo, /multi tarefa1 || tarefa2 e /skills. A geração livre ainda é limitada."
        )
    if lower.startswith("/self") or lower in {"quem é você", "quem e voce", "me fale sobre você", "me fale sobre voce"}:
        return (
            "Sou ULTRON. Uso um classificador de intenções próprio, treinado do zero, com tokenizador byte/word e habilidades locais. Não uso Gemini, OpenAI, Claude, modelos pré-treinados ou tokens de provedores. Ainda não sou um LLM generativo geral."
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
            f"Vou usar a estratégia local {strategy}.\n"
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
    # A deterministic decoder must not pretend that echoing the prompt is an answer.
    recent_context = [str(item).strip() for item in history if str(item).strip()]
    if recent_context:
        return (
            "Quero continuar a partir do contexto anterior, mas minha camada de linguagem "
            "ainda não consegue inferir com segurança o que você quis dizer. "
            "Pode explicar qual resultado espera ou qual parte devo resolver? "
            "Posso executar cálculos, planejamento estruturado, pesquisa web e habilidades locais."
        )
    return (
        "Ainda não consegui interpretar essa solicitação com segurança. "
        "Pode reformular em uma frase ou dizer qual resultado espera? "
        "Consigo executar cálculos, planejamento estruturado, pesquisa web e habilidades locais. "
        "Minha geração de linguagem aberta ainda é experimental; não vou inventar uma resposta."
    )
