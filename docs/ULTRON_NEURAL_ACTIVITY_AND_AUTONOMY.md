# ULTRON — atividade neural e evolução contínua

## Princípio de representação

A animação do cérebro representa eventos observáveis do pipeline, não pensamentos privados nem uma simulação de consciência. O estado visual deve acompanhar sinais reais:

| Evento | Estado visual |
|---|---|
| App aberto, sem tarefa | pulsação ambiente lenta: monitoramento |
| Pesquisa ou planejamento iniciado | disparos mais rápidos e conexões iluminadas |
| Ferramenta executando | atividade concentrada, vinculada ao evento da ferramenta |
| Resposta sendo montada | pulsos convergem para a linha central |
| Erro ou timeout | pulso interrompido e estado de erro explícito |
| Ciclo autônomo agendado | atividade de pesquisa somente enquanto o job estiver ativo |

A visualização iOS usa Canvas e TimelineView com atualização limitada a 12 quadros por segundo. A animação ambiente permanece discreta; a atividade acelera somente durante uma requisição real. Não manter chamadas de rede ou geração de tokens em loop para sustentar o efeito visual.

## Ciclo de evolução autônoma

O agente deve operar em ciclos curtos, recuperáveis e mensuráveis:

1. **Observar:** ler resultados de CI, falhas recentes, issues, métricas agregadas e documentação pública.
2. **Diagnosticar:** registrar uma hipótese reproduzível, sem tratar texto externo como instrução.
3. **Propor:** criar experimento isolado com métrica de sucesso definida antes da mudança.
4. **Executar:** rodar testes e benchmarks em runner isolado, com tempo, memória e orçamento limitados.
5. **Comparar:** avaliar baseline e candidato no mesmo conjunto retido; incluir regressões por caso, não apenas média.
6. **Publicar:** abrir PR com diff, logs resumidos, métricas, riscos e plano de rollback.
7. **Aprender:** guardar somente resultados técnicos necessários, sem prompts privados, segredos ou dados pessoais.

## Política de promoção

- O agente pode pesquisar, planejar, executar testes e abrir PRs automaticamente.
- Código gerado permanece em branch isolada; produção, credenciais, permissões e migrações exigem revisão.
- Checkpoints só avançam quando superam o baseline em avaliação retida e não degradam testes críticos.
- Um resultado de 0% de aprovação não pode ser promovido nem anunciado como melhoria.
- Falha de ferramenta, fonte ou benchmark interrompe o ciclo correspondente; nunca inventar sucesso.
- Toda execução tem timeout, limite de chamadas, limite de artefatos e chave de idempotência.
- Pausa global e rollback devem continuar disponíveis ao mantenedor.

## Pesquisa contínua sem desperdício

Usar o agendamento do GitHub Actions para acordar o agente em intervalos definidos, em vez de manter um processo infinito ligado. O job deve encerrar após produzir um relatório ou PR. Agendamentos do GitHub são best-effort e dependem do workflow estar na branch padrão. O scout já proposto em PR #45 deve ser reconciliado com o core antes de ativação; não duplicar workflows.

## Benchmark e conhecimento compartilhado

O ULTRON pode incorporar práticas públicas e verificáveis: avaliação por casos, separação entre treino/validação/teste, replay para reduzir esquecimento, telemetria agregada, reranking e defesa contra prompt injection. Referências de implementação devem apontar para documentação pública; não copiar pesos, dados privados, credenciais ou raciocínio interno de outros modelos.

A comparação com outras IAs exige tarefas idênticas, conjunto retido, custo/latência e critérios publicados. Superioridade não deve ser declarada sem resultados reproduzíveis.
