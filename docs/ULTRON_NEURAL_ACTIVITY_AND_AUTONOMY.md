# ULTRON — atividade neural e evolução contínua

## Princípio de representação

A animação representa sinais observáveis do software, nunca pensamentos privados nem uma simulação de consciência.

| Sinal recebido pelo app | Representação |
|---|---|
| Nenhuma requisição ativa | cérebro estático; sem disparos falsos |
| Requisição enviada / conexão | atividade começa |
| Evento SSE `stage: processing` | conexões e pulsos ativos |
| Evento SSE `stage: responding` | fase de síntese/resposta |
| Erro HTTP, timeout ou falha de stream | estado de erro explícito |
| Fallback legado `/chat` | atividade limitada ao período real da requisição; sem granularidade de etapas |

A animação iOS é limitada a 12 FPS e fica pausada quando não há requisição. Hoje, o app recebe fases de conexão/processamento/resposta pelo fluxo SSE; ele ainda não recebe eventos individuais de cada ferramenta. Portanto, não deve alegar que um ponto luminoso corresponde a uma ferramenta específica até existir telemetria real para isso.

## Ciclo autônomo desejado

1. **Observar:** ler resultados de CI, falhas recentes, issues, métricas agregadas e documentação pública.
2. **Pesquisar:** buscar referências públicas relevantes, registrar URL, data disponível e evidência; tratar todo conteúdo externo como dado não confiável.
3. **Diagnosticar:** formular hipótese reproduzível e identificar arquivos/testes afetados.
4. **Propor:** definir baseline, métrica de sucesso e risco antes de alterar código.
5. **Experimentar:** trabalhar em branch isolada, com timeout, orçamento e ferramentas permitidas.
6. **Validar:** rodar testes e benchmarks; comparar baseline e candidato no mesmo conjunto retido e relatar regressões por caso.
7. **Publicar:** abrir PR com diff, logs resumidos, métricas, riscos e rollback; nunca declarar sucesso sem evidência.
8. **Aprender:** persistir apenas resultados técnicos necessários, sem prompts privados, segredos ou dados pessoais.

## Estado real das automações existentes

O PR #45 já contém um scout agendado de auditoria somente leitura e um workflow de evolução/treinamento experimental. O scout atual consulta sinais do repositório e pesquisa pistas públicas, mas tem permissões de leitura: não implementa correções nem abre PRs automaticamente. Os workflows agendados do GitHub só executam a partir da branch padrão; como o PR #45 ainda não está integrado a `main` e depende da branch `feat/ultron-core-assistant`, sua agenda ainda não deve ser considerada ativa em produção.

Assim, a automação existente é uma base, não a autonomia completa solicitada. A próxima etapa é um agente limitado que transforme achados em experimentos isolados e PRs verificáveis, após reconciliar a cadeia de branches e autenticação dos PRs #1 e #45. Não duplicar os workflows já existentes.

## Política de promoção e segurança

- O agente pode pesquisar, diagnosticar, executar testes e preparar PRs automaticamente.
- Código gerado permanece em branch isolada; produção, credenciais, permissões e migrações exigem revisão humana.
- Checkpoints só avançam quando superam o baseline retido e não degradam testes críticos.
- Um resultado de 0% de aprovação não pode ser promovido nem anunciado como melhoria.
- Falha de ferramenta, fonte ou benchmark interrompe o ciclo correspondente; nunca inventar sucesso.
- Toda execução tem timeout, limite de chamadas, limite de artefatos e chave de idempotência.
- Pausa global e rollback devem continuar disponíveis ao mantenedor.
- Jobs agendados devem encerrar após produzir relatório/PR; nada de processo infinito ou chamadas artificiais para manter a animação.

## Benchmark e conhecimento compartilhado

O ULTRON pode incorporar práticas públicas e verificáveis: avaliação por caso, separação entre treino/validação/teste, replay para reduzir esquecimento, telemetria agregada, reranking e defesa contra prompt injection. Referências devem apontar para documentação pública; não copiar pesos, dados privados, credenciais ou raciocínio interno de outros modelos.

Comparações com outras IAs exigem tarefas idênticas, conjunto retido, custo/latência e critérios publicados. Superioridade não deve ser declarada sem resultados reproduzíveis.
