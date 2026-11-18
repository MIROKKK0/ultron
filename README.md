# ULTRON

Assistente pessoal em português com app nativo para iPhone, API HTTPS, memória protegida, ferramentas e núcleo local independente de provedores, com adaptador generativo externo opcional. O classificador local continua disponível como fallback; o modelo generativo não é treinado do zero pelo projeto.

## Componentes

- App SwiftUI para iPhone (iOS 16+).
- Backend FastAPI.
- PostgreSQL em produção ou SQLite para desenvolvimento local.
- Chat, pesquisa e status públicos com limite básico por IP; sem token manual no iPhone. O chat público é temporariamente sem memória persistente para não expor dados entre instalações. Rotas administrativas e de memória continuam protegidas.
- Classificador de intenções próprio treinado do zero (225 exemplos, tokenizador UTF-8 próprio de 4096 IDs); skills nativas e fallback determinístico. Ele não substitui um LLM generativo.
- Pesquisa web sem chave via metabusca DDGS, com links para as fontes; testes Python e GitHub Actions para CI, simulador e IPA.
- Skills nativas de conversa, planejamento, diagnóstico, memória protegida e autoevolução segura; feedback não altera pesos do classificador.

## Backend local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ULTRON_API_TOKEN="crie-um-token-forte"
python ultron.py --host 0.0.0.0
```

A API local fica em `http://localhost:8000`; a documentação interativa fica em `/docs`.

## Recursos do agente

Com Bearer token, o backend oferece:
- `GET /self`: identidade, capacidades e estado de configuração.
- `POST /agent/plan` com `{"goal":"..."}`: plano de tarefa, risco e necessidade de aprovação.
- `POST /reflect`: checklist heurístico de uma resposta.
- `POST /improvement-proposals`: proposta testável, sem aplicar alterações automaticamente.
- `GET /benchmarks`: casos internos de fumaça.
- `GET /brain/status`: estado da orquestração, classificador próprio e limites do decodificador.
- `GET /skills`: catálogo de habilidades nativas.
- `POST /skills/run` (autenticado): executa uma habilidade instalada.
- `POST /brain/research`: retorna 503 até existir uma implementação de pesquisa local sem serviços externos.
- `POST /brain/run` com `{"goal":"..."}`: ciclo cognitivo com planejador, solucionador, crítico e síntese.
- `POST /brain/multitask` com `{"tasks":["...","..."]}`: até cinco tarefas independentes em paralelo.
- `POST /feedback` com avaliação de 1 a 5 e comentário opcional.
- `GET /feedback/summary`: média de avaliações armazenadas.

O chat público não lê nem grava memória/conversas compartilhadas até existir uma identidade segura por instalação. O app envia até oito mensagens recentes do histórico local como contexto temporário. O classificador próprio identifica intenções comuns e chama skills locais em milissegundos; para conversas gerais, o backend usa o modelo generativo configurado e mantém o fallback local quando nenhuma chave estiver configurada. Rotas administrativas protegidas mantêm a memória persistente. No chat do iPhone, use `/self`, `/plan seu objetivo`, `/research sua pergunta` e `/calc 12*(3+4)`. O endpoint `/brain/run` executa planner, solver e critic locais e gera uma síntese determinística. Use `/research sua pergunta` para pesquisar na internet; o ULTRON retorna trechos e links de fontes. A busca não usa LLM para sintetizar e pode falhar se o mecanismo de pesquisa bloquear o servidor. `/brain/multitask` aceita até cinco tarefas. Feedback explícito do usuário calibra apenas a prioridade de planner/solver/critic, com ajuste limitado a ±15% e limite de 10 avaliações por hora/IP. Isso não treina pesos do modelo de linguagem. O módulo experimental de associação usa codificador esparso, recompensa e decaimento; seu estado é salvo no banco.

Para PostgreSQL, defina `DATABASE_URL`. O núcleo funciona sem chaves externas. Um endpoint OpenAI-compatible é opcional e só é ativado quando `ULTRON_LLM_API_KEY`, `ULTRON_LLM_BASE_URL` e `ULTRON_LLM_MODEL` são configurados juntos. Remover essas variáveis mantém ULTRON em modo local, sem perda de memória ou identidade. O chat e a pesquisa públicos têm limites por IP; memória e rotas administrativas continuam exigindo `ULTRON_API_TOKEN`.

Nunca coloque chaves de provedor ou tokens em commits, no app ou em arquivos públicos. Cadastre-os como variáveis secretas no serviço de hospedagem.

## Hospedagem Render

O serviço configurado é:

- API: https://ultron-api-c5ae.onrender.com
- Região: Virginia
- Plano: Free
- Banco PostgreSQL: plano Free, com expiração indicada pelo Render em 15/12/2026.

O arquivo `render.yaml` conecta `DATABASE_URL` ao banco e define `/health` como health check. O rate limit atual é em memória por instância; antes de escalar, trocar por quota compartilhada no PostgreSQL e ativar App Attest. A memória privada só deve voltar ao chat depois do isolamento por instalação. A memória associativa experimental é persistida como checkpoint separado. A sincronização do Blueprint precisa ser aprovada no painel do Render. O Postgres Free existente expira em 15/12/2026 e tem limite de 1 GB; é adequado para teste, não para dados permanentes. O serviço web Free pode dormir após 15 minutos sem tráfego e o SQLite local é efêmero.

Após aprovar a sincronização do Blueprint, `ULTRON_API_TOKEN` é gerado pelo Render e `DATABASE_URL` é conectado ao Postgres. O token Bearer protege a API; ele não habilita nem paga um provedor de IA.

## App iOS e IPA

O projeto Xcode é gerado com XcodeGen:

```bash
brew install xcodegen
xcodegen generate
open ULTRON.xcodeproj
```

O workflow `ULTRON iOS Build` compila para simulador e gera um IPA arm64 sem assinatura para o SideStore assinar no próprio iPhone. O app consulta `/health` para mostrar o estado real da API. O IPA só estará disponível depois que o job `device-ipa` terminar com sucesso.

No app, abra Configurações e confirme a URL HTTPS da API. O chat e a pesquisa não pedem token.

Depois, instale o IPA pelo SideStore. A compilação de simulador não pode ser instalada diretamente no iPhone.

## Segurança

- As rotas públicas de chat e pesquisa aplicam limites básicos por IP; memória e rotas administrativas exigem Bearer token.
- Chaves de provedores ficam apenas nos secrets do Render; nunca no repositório nem no app iOS.
- O ULTRON não executa comandos arbitrários nem contorna autenticação ou assinaturas.
- Ações externas ou irreversíveis exigem confirmação explícita.


### Aprendizagem neural experimental

- `backend/neural_learning.py` implementa codificação lexical esparsa e associações pré/pós-atividade moduladas por recompensa, com pesos limitados, decaimento e checkpoint.
- `POST /brain/learn` e `POST /brain/recall` são rotas protegidas para experimentos controlados.
- A memória associativa funciona de forma independente da orquestração e pode ser consultada por contexto.
- O feedback explícito no aplicativo atualiza apenas prioridades das estratégias, com limites; não modifica os pesos de um LLM.
- Isso é uma camada computacional inspirada em aprendizagem biológica, não uma reprodução completa do mushroom body nem prova de inteligência geral.

## Modelo próprio e treino

O modelo atual é um classificador de intenções Naive Bayes com tokenizador próprio UTF-8/word n-gram, 4096 IDs hash e pesos treinados a partir de `training/intent_corpus.jsonl`. Para retreinar: `python scripts/train_intent_model.py`; para verificar que o artefato corresponde ao corpus: `python scripts/train_intent_model.py --check`. O workflow semanal verifica o treino reproduzível. Isso não é um modelo generativo geral; perguntas abertas continuam limitadas até existir treino generativo em escala adequada.


## Monitor holográfico e integração com iPhone

O cabeçalho do app usa Canvas/TimelineView para desenhar o monitor procedural do
ULTRON. O endpoint `POST /chat/stream` informa quando o servidor está processando
e quando a resposta chega. O app também oferece copiar, ler em voz alta,
compartilhar e a ação "Perguntar ao ULTRON" pelo Atalhos/Siri.

## Núcleo generativo experimental

`training/generative/` contém um Transformer causal próprio, inicializado do
zero, com tokenizador byte-level e corpus autoral pequeno. Ele é separado do
classificador de intenções de produção e ainda não está integrado ao chat.
Consulte `training/generative/README.md`; o checkpoint resultante é experimental
e não equivale a um modelo de linguagem grande.
