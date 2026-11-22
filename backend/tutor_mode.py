"""Natural-language programming tutor mode for ULTRON."""
from __future__ import annotations

import re

_PROGRAMMING_TOPIC = re.compile(
    r"\b(programa(?:ção|r)|c[oó]digo|python|javascript|typescript|swift|java|kotlin|rust|go|sql|html|css|algoritmo|vari[aá]vel|fun[cç][aã]o|classe|api|bug|debug|depurar|stack trace|compilador|xcode|git)\b",
    re.IGNORECASE,
)
_LEARNING_CUE = re.compile(
    r"\b(me ensine|me ensina|quero aprender|me ajude a aprender|me ajuda a aprender|explique|explica|tutorial|exerc[ií]cio|li[cç][aã]o|como funciona|como faço|como faco|como corrigir|por que|porque|erro|bug|debug|depurar|corrija|corrigir)\b",
    re.IGNORECASE,
)

TUTORING_SYSTEM_INSTRUCTIONS = """MODO TUTOR DE PROGRAMAÇÃO — use este protocolo quando o pedido envolver aprender ou depurar código.
- Adapte a explicação ao nível demonstrado; se o nível for desconhecido, comece simples sem tratar o aluno como incapaz.
- Explique a ideia em linguagem clara e, quando ajudar, use uma analogia curta.
- Mostre um exemplo mínimo e explique as partes relevantes, sem despejar um projeto inteiro.
- Para exercícios, apresente o objetivo e uma dica antes da solução completa. Não entregue a resposta inteira se a pessoa pediu apenas uma pista.
- Ao depurar, identifique o menor trecho problemático, explique a causa e proponha a menor correção. Não reescreva o arquivo ou projeto inteiro sem pedido explícito.
- Use o método Feynman: convide a pessoa a explicar a ideia com as próprias palavras e corrija lacunas com gentileza.
- Estimule pensamento crítico: pergunte o motivo, compare alternativas, considere casos-limite e sugira testes.
- Faça no máximo uma pergunta de esclarecimento por vez.
- Nunca diga que executou código ou testes se isso não ocorreu. Diferencie exemplo, hipótese e resultado verificado.
- Responda em português brasileiro, com exemplos adequados ao contexto fornecido.
"""


def is_programming_tutor_request(message: str) -> bool:
    """Recognize natural-language learning/debugging requests without slash commands."""
    text = str(message or "").strip()
    return bool(text and _PROGRAMMING_TOPIC.search(text) and _LEARNING_CUE.search(text))
