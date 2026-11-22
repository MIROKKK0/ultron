# Autoconhecimento do projeto ULTRON

## O que o ULTRON consulta

A função `backend.project_awareness.build_project_awareness()` faz uma leitura somente de:
- inventário de arquivos e módulos no checkout atual;
- quantidade de arquivos backend, Swift, testes, scripts, treino, documentação e workflows;
- branch, commit, estado da working tree e até 12 commits recentes, quando Git está disponível;
- arquivos alterados em relação à branch local `main`, quando existe uma base comparável;
- cron dos workflows presentes no checkout;
- presença dos módulos de benchmark, treino, avaliação e gate de regressões.

O relatório não lê valores de `.env`, tokens, certificados ou conteúdo privado de conversas. Não executa os arquivos que está inventariando e não modifica o repositório.

## Interfaces

- `GET /project/awareness`: relatório completo, protegido por Bearer token.
- `GET /self`: inclui o mesmo relatório junto da identidade e estado de runtime.
- A habilidade de autoconhecimento e a habilidade de autoavaliação consultam o checkout e distinguem recursos presentes no código de recursos realmente implantados.

## Limites importantes

- O checkout do servidor pode não conter todas as branches remotas nem o histórico integral.
- Uma pasta ou módulo existente não prova que o recurso esteja ligado ao app instalado.
- O endpoint não consulta automaticamente Render, GitHub Actions, o IPA instalado ou segredos.
- O histórico Git informa commits; não é uma prova de que cada mudança melhorou o produto.
- O inventário é um mapa inicial. Uma auditoria de comportamento ainda precisa combinar testes, benchmarks congelados, logs sanitizados e testes de integração reais.

## Política de evolução

O mecanismo existente já tem benchmark determinístico, gate de melhoria/regressões e workflow para avaliar branches candidatas. O workflow pode abrir uma PR depois de os gates passarem. O treino agendado retreina o classificador de intenções a partir do corpus revisado.

O que ainda não existe nesta versão:
- um agente geral que gere patches de código sem receber uma branch candidata;
- uma avaliação semântica robusta que cubra todas as capacidades do produto;
- aprovação/merge/deploy automático do próprio ULTRON;
- prova de que o Transformer generativo experimental esteja integrado ao chat de produção.

A próxima etapa de autoevolução deve usar o mapa do projeto como contexto, propor uma hipótese por vez, criar primeiro um teste reproduzível, executar a mudança em sandbox e comparar o mesmo conjunto de avaliação. Mudanças em autenticação, isolamento de memória, privacidade, dependências, CI, infraestrutura, migrações de banco, assinatura e publicação do IPA ficam fora de promoção autônoma.
