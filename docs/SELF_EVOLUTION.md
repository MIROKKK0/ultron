# ULTRON — skills e autoevolução segura

## Núcleo leve atual

- Classificador de intenções próprio, treinado do zero com 225 exemplos em português.
- Tokenizador próprio de bytes UTF-8, palavras e n-gramas, com 4096 IDs hash.
- Multinomial Naive Bayes com pesos próprios versionados em `backend/model/intent_model.json`.
- Inferência na CPU usando apenas a biblioteca padrão do Python; sem downloads de modelos, GPU ou provedores externos.
- Skills nativas: conversa, ajuda, autoconhecimento, planejamento, cálculo/pesquisa via ferramentas existentes, status, memória protegida, autoavaliação e autoevolução segura.

## Limite explícito

O modelo é um classificador de intenções, não um LLM generativo. Ele aprende a encaminhar pedidos conhecidos para habilidades locais; perguntas abertas continuam limitadas pelo decodificador determinístico. Não deve ser anunciado como equivalente ao ChatGPT ou como inteligência geral.

## Ciclo de evolução

1. Medir a qualidade em conjunto de validação fixo.
2. Revisar exemplos novos antes de adicioná-los ao corpus.
3. Treinar pesos novamente com `python scripts/train_intent_model.py`.
4. Verificar reprodutibilidade com `python scripts/train_intent_model.py --check`.
5. Executar toda a suíte de testes e medir latência/RAM.
6. Abrir PR com corpus, pesos, métricas e regressões.
7. Exigir revisão humana antes de integrar ou implantar.

Feedback público, páginas da web e mensagens de usuários não são incorporados automaticamente ao corpus. Isso evita envenenamento de dados, prompt injection e gravação de informações pessoais. Skills são funções Python internas; arquivos externos de skills são documentação e nunca são executados como código.


## Estado real da automação no GitHub

O workflow `.github/workflows/model-training.yml` foi configurado para executar
diariamente às 14:17 UTC (11:17 no horário de Brasília): retreina o classificador
a partir apenas do corpus revisado, verifica a reprodutibilidade, executa testes,
mede latência/RSS e publica um relatório de execução por 14 dias. Também pode
ser iniciado manualmente.

A automação não lê conversas privadas, não adiciona dados automaticamente,
não modifica o código de produção e não faz merge ou deploy. Agendamento do
GitHub Actions passa a executar quando o workflow estiver na branch padrão do
repositório; enquanto estiver apenas nesta PR, a execução pode ser disparada
manualmente.


## Autoevolução recursiva do código

O worker `scripts/recursive_evolution.py` acrescenta um ciclo real de engenharia de software:
- inspeciona o mapa do projeto, histórico e skills;
- pesquisa fontes públicas e vídeos técnicos com a ferramenta web já usada pelo ULTRON;
- escolhe uma melhoria e gera um patch unified diff;
- aplica o patch apenas num checkout efêmero e numa branch candidata;
- executa a suíte de testes e o benchmark congelado;
- faz uma segunda chamada de revisão crítica sobre o diff e o resultado dos testes;
- abre uma PR e pode incorporá-la automaticamente apenas em `feat/ultron-core-assistant` depois que os checks de CI passarem.

O endpoint autenticado `POST /evolution/dispatch` e a skill `recursive_evolution` permitem ao ULTRON disparar o worker. O workflow agendado fica no branch padrão e faz checkout explícito do ramo de desenvolvimento.

### Configuração necessária

Adicionar como GitHub Actions secrets:
- `ULTRON_LLM_API_KEY`
- `ULTRON_LLM_BASE_URL` (endpoint HTTPS compatível com OpenAI Chat Completions)
- `ULTRON_LLM_MODEL`

O Render precisa de `ULTRON_GITHUB_TOKEN` com permissão Actions: write no repositório para que a API/skill dispare o workflow. Nenhum desses segredos deve ser gravado no código, no IPA ou em artefatos públicos.

### O que evolui automaticamente

O ciclo pode alterar backend, cliente iOS, skills, documentação, scripts, treinamento e testes. Mantém histórico de branches e PRs para que o ULTRON compare versões e aprenda com os resultados de ciclos anteriores.

O worker não edita diretamente o checkout de produção, não lê segredos, não modifica workflows/infraestrutura/autenticação, não publica IPA e não implanta Render. A incorporação automática é limitada ao ramo de desenvolvimento; a publicação em `main` continua sendo um release separado.

O modelo local de intenção continua sendo um classificador, não um LLM. A geração de patches depende do provedor de código configurado; sem as três secrets de LLM, o worker para com uma mensagem explícita em vez de fingir que evoluiu.
