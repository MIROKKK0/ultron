# ULTRON — skills e autoevolução segura

## Núcleo atual

- Classificador de intenções próprio, treinado com corpus revisado em português.
- Tokenizador próprio e inferência leve na CPU.
- Skills nativas para conversa, planejamento, cálculo, pesquisa, status, memória, autoavaliação e autoconhecimento.
- Mapa somente leitura do repositório e do histórico Git disponível no checkout, documentado em [PROJECT_AWARENESS.md](PROJECT_AWARENESS.md).

O classificador de intenções não é um LLM generativo geral. A presença de um módulo Transformer ou de um adaptador de provedor não prova que esteja carregado no runtime de produção.

## O que o ciclo já faz

1. Mantém um benchmark determinístico em português e um conjunto de testes.
2. Avalia uma branch candidata contra a versão-base.
3. Exige ganho mensurável e ausência de regressões nos critérios congelados.
4. Abre uma PR depois da avaliação, quando acionado pelo fluxo autorizado.
5. Marca PRs com `ultron-eligible-for-promotion` somente quando os gates passam e os arquivos alterados estão na lista de baixo risco; outros caminhos recebem `ultron-human-review-required`.
6. O merge e o deploy continuam separados da aprovação técnica.

## Proteções do gate

O avaliador e o comparador são lidos da branch-base e usados tanto para baseline quanto para candidato. O candidato não pode mudar os próprios critérios, o comparador, o workflow de evolução ou as dependências do ambiente de teste. O CI executa os testes novos do candidato e também a suíte da versão-base contra o código candidato, impedindo que uma alteração apague testes antigos para parecer melhor.

Mudanças em autenticação, memória e isolamento de usuários, banco/migrações, dependências, workflows, infraestrutura, assinatura e publicação do IPA exigem revisão humana. O gate mede somente o que os casos cobrem; um score maior não prova inteligência geral nem ausência de bugs desconhecidos.

## O que ainda não faz

- Não existe ainda um gerador geral que escreva patches de software por iniciativa própria.
- Não aprende automaticamente com conversas privadas nem altera pesos do Transformer a partir de feedback.
- O endpoint de feedback informa explicitamente que não é usado para treino do modelo; a calibração permitida é limitada à prioridade de estratégias.
- Não aprova nem faz merge/deploy irrestrito para produção.
- Não consegue afirmar que o código no servidor ou no IPA é o mesmo checkout sem consultar o deploy/versão correspondente.

## Treino agendado

O workflow `.github/workflows/model-training.yml` retreina apenas o classificador de intenções a partir do corpus revisado. Ele não treina um LLM geral. O cron definido é diário às 14:17 UTC (11:17 em Brasília), mas o agendamento do GitHub Actions só é executado na branch padrão. Como a arquitetura cognitiva ainda está em uma branch diferente de `main`, esse cron não deve ser considerado ativo até a integração na branch padrão.

## Próxima etapa de evolução

Conectar um agente de programação como proponente opcional (nunca como autoridade), capaz de gerar hipóteses e patches pequenos. ULTRON deve manter o contexto, a política de segurança, os benchmarks, a decisão de promoção e o registro de experimentos. O ciclo recomendado é: observar falha → criar teste → propor uma alteração isolada → executar baseline e candidato com a mesma régua → manter ou descartar → registrar o resultado → abrir PR.
