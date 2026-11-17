---
name: improve-codebase-architecture
description: Analisa a arquitetura do projeto, encontra pontos de acoplamento e propõe melhorias incrementais sem alterar código automaticamente.
---

# Improve Codebase Architecture

Objetivo: tornar o Ultron mais fácil de manter, testar e evoluir, sem quebrar seu núcleo.

## Regras obrigatórias

- Primeiro mapear a arquitetura e ler decisões/documentação existentes.
- Identificar módulos com responsabilidades misturadas, dependências circulares, interfaces rasas e código difícil de testar.
- Para cada proposta, explicar arquivos afetados, problema observado, mudança mínima, risco, benefício e testes necessários.
- Aplicar o teste de remoção: se o módulo desaparecesse, a complexidade ficaria concentrada atrás de uma interface menor ou apenas se espalharia? Só recomendar o primeiro caso.
- Preservar comportamento público e compatibilidade; evitar reescritas amplas.
- Fazer uma mudança por vez, em branch separada.
- Adicionar ou atualizar testes e executar a suíte relevante.
- Nunca alterar prompts, memória persistida, chaves, configurações ou dados do usuário como efeito colateral.
- Não modificar a branch principal nem fazer merge automaticamente.
- Se evidências forem insuficientes, apresentar hipótese e pedir validação em vez de afirmar que existe um defeito.

## Formato do relatório

1. Estado atual e limites conhecidos.
2. Até cinco oportunidades priorizadas (ou declarar que não há evidência suficiente).
3. Para cada oportunidade: arquivos, evidência, proposta, risco, ganho de testabilidade e plano de verificação.
4. Uma recomendação inicial de baixo risco.
5. Parar antes de implementar mudanças estruturais não aprovadas.
