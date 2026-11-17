# ULTRON: evolução automática com validação

## O que a automação faz

O workflow `.github/workflows/ultron-autonomous-evolution.yml` executa treinamento e avaliação em runners efêmeros do GitHub Actions. O fluxo atual:

1. Reproduz o modelo determinístico de intenções.
2. Executa a suíte de regressão Python.
3. Mede o roteamento de intenções.
4. Treina ULTRON Tiny com pesos inicializados aleatoriamente, usando somente o corpus versionado do projeto.
5. Recarrega o checkpoint salvo, valida a compatibilidade do estado e gera texto em CPU.
6. Registra perda de validação, perplexidade, número de parâmetros, latência de geração e pico de RAM do runner.
7. Publica checkpoint e relatórios como artefatos temporários do GitHub Actions.

O workflow separado `ptbr-pretraining.yml` prepara um corpus de livros brasileiros de domínio público, cria splits 80/10/10 por hash, treina um BPE próprio e executa um pré-treino maior. Ele fica agendado semanalmente (domingo, 11:17 BRT) e também pode ser disparado manualmente. O fluxo diário leve e o pré-treino semanal têm custos e objetivos diferentes.

## Limites deliberados

- Um checkpoint experimental nunca substitui automaticamente pesos de produção.
- O workflow não altera código, não faz merge e não faz deploy.
- O benchmark de RAM/latência é medido no runner Linux; não representa o iPhone nem o serviço de hospedagem.
- A execução diária de `schedule` só ocorre quando o workflow está presente na branch padrão (`main`). Execuções de PR validam a proposta, mas não ativam o cron.
- O modelo atual é pequeno, treinado do zero e limitado pelo volume e diversidade do corpus. Uma perda menor no mesmo corpus não prova capacidade geral, raciocínio ou equivalência ao ChatGPT.
- O dataset de livros declara CC0-1.0, mas o próprio cartão informa que não foi sanitizado de PII e pode conter nomes, contatos e vieses. A limpeza por regex não é garantia de anonimização; revisar amostras e filtrar conteúdo antes de distribuir artefatos.

## Como evoluir com segurança

A próxima etapa é ampliar o corpus com fontes permitidas e documentar licenças, manter conjuntos separados de treino/validação/teste, criar avaliações de comportamento em português e comparar cada candidato com a versão estável. Só promover um checkpoint se ele melhorar tarefas retidas sem regressões de segurança, qualidade, latência e memória. Guardar sempre o checkpoint anterior para rollback.

Para autoevolução de código, o agente deve operar em branch isolada, propor um PR pequeno, executar CI e nunca obter permissão de merge/deploy automático. Dados de conversas privadas não devem ser usados como corpus de treino sem consentimento explícito e anonimização adequada.
