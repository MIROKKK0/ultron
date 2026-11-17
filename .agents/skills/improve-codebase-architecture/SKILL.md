---
name: improve-codebase-architecture
description: Audita a arquitetura do ULTRON, identifica oportunidades de modularidade, testabilidade e navegação por agentes sem alterar código automaticamente.
---

# Improve Codebase Architecture

Faça auditorias periódicas para tornar o ULTRON mais fácil de manter e evoluir. Esta skill produz um diagnóstico e propostas; não aplica refatorações automaticamente.

## Contexto obrigatório

Leia `AGENTS.md`, `README.md`, decisões em `docs/` e o histórico recente antes de avaliar mudanças. Respeite a arquitetura neural documentada e os limites científicos do FlyBrain/FlyWire.

## O que procurar

- Responsabilidades misturadas em módulos grandes.
- Acoplamento que força alterações em muitos arquivos.
- Interfaces difíceis de testar sem iniciar infraestrutura pesada.
- Regras de segurança duplicadas ou inconsistentes.
- Testes frágeis, ausentes ou que dependem de estado global.
- Código de runtime que não corresponde às capacidades declaradas na documentação.

## Critérios para recomendar

Para cada oportunidade, aplique o teste de remoção: se o módulo desaparecesse, a complexidade ficaria concentrada atrás de uma interface menor ou apenas se espalharia? Recomende somente quando houver evidência concreta de concentração e ganho.

Apresente no máximo cinco oportunidades, ordenadas por impacto e risco. Para cada uma, informe:
- arquivos e evidências observadas;
- problema concreto, sem especulação;
- proposta mínima e interfaces envolvidas;
- impacto sobre FlyBrain, linguagem, memória, API e iOS;
- riscos, rollback e compatibilidade;
- testes que devem ser adicionados ou preservados;
- métrica verificável de sucesso.

## Regras de execução

- Não alterar código durante a auditoria.
- Não sugerir trocar o FlyBrain por um LLM nem ativar o conectoma completo sem validação de memória e desempenho.
- Não alterar pesos, sinapses, datasets, segredos, dados de usuários ou infraestrutura.
- Se o usuário escolher uma proposta, implementar uma mudança por vez em branch isolada.
- Rodar a suíte de testes relevante e registrar resultados reais.
- Abrir PR; não fazer merge ou deploy.
- Se a evidência for insuficiente, registrar uma pergunta de investigação, não um defeito confirmado.

## Resultado

Entregue um relatório curto com estado atual, evidências, oportunidades priorizadas, primeira recomendação de baixo risco e comandos/testes para verificar a mudança. Pare e aguarde escolha antes de refatorar.
