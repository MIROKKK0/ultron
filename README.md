# ULTRON

Assistente pessoal em português com app nativo para iPhone, API HTTPS e memória persistente, sem simulação neural experimental e sem API externa de IA.

## Componentes

- App SwiftUI para iPhone (iOS 16+).
- Backend FastAPI.
- PostgreSQL em produção ou SQLite para desenvolvimento local.
- Chat, pesquisa e status públicos com limite básico por IP; o app registra uma identidade aleatória por instalação e guarda a credencial no iOS Keychain. A memória é isolada por instalação; revogar uma instalação apaga apenas seus próprios registros.
- Classificador de intenções próprio treinado do zero (225 exemplos, tokenizador UTF-8 próprio de 4096 IDs); skills nativas e fallback determinístico. Não é um LLM generativo e não exige modelos ou tokens externos.
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
- `POST /brain/research`: pesquisa web pública sem chave via DDGS e devolve trechos e links; não usa um LLM para sintetizar os resultados.
- `POST /brain/run` com `{"goal":"..."}`: ciclo cognitivo com planejador, solucionador, crítico e síntese.
- `POST /brain/multitask` com `{"tasks":["...","..."]}`: até cinco tarefas independentes em paralelo.
- `POST /feedback` com avaliação de 1 a 5 e comentário opcional.
- `GET /feedback/summary`: média de avaliações armazenadas.

Cada instalação do iPhone recebe uma credencial aleatória própria, armazenada no Keychain. As rotas de memória e a recuperação contextual no chat verificam essa credencial e nunca compartilham lembranças entre instalações. O classificador próprio identifica intenções comuns e chama skills locais; o fallback determinístico continua disponível para entradas desconhecidas. No chat do iPhone, use `/self`, `/plan seu objetivo`, `/research sua pergunta`, `/calc 12*(3+4)`, `/remember texto`, `/memories` e `/forget ID`. O endpoint `/brain/run` executa planner, solver e critic locais e gera uma síntese determinística. Use `/research sua pergunta` para pesquisar na internet; o ULTRON retorna trechos e links de fontes. A busca não usa LLM para sintetizar e pode falhar se o mecanismo de pesquisa bloquear o servidor. `/brain/multitask` aceita até cinco tarefas. Feedback explícito do usuário calibra apenas a prioridade de planner/solver/critic, com ajuste limitado a ±15% e limite de 10 avaliações por hora/IP. Isso não treina pesos do modelo de linguagem. O módulo experimental de associação usa codificador esparso, recompensa e decaimento; seu estado é salvo no banco.

Para PostgreSQL, defina `DATABASE_URL`. Nenhuma chave de provedor de IA é necessária. O chat e a pesquisa públicos têm limites por IP; memória e rotas administrativas continuam exigindo `ULTRON_API_TOKEN`.

Nunca coloque chaves de provedor ou tokens em commits, no app ou em arquivos públicos. Cadastre-os como variáveis secretas no serviço de hospedagem.

## Hospedagem Render

O serviço configurado é:

- API: https://ultron-api-c5ae.onrender.com
- Região: Virginia
- Plano: Free
- Banco PostgreSQL: plano Free, com expiração indicada pelo Render em 15/12/2026.

O arquivo `render.yaml` conecta `DATABASE_URL` ao banco e define `/health` como health check. O rate limit atual é em memória por instância; antes de escalar, trocar por quota compartilhada no PostgreSQL e ativar App Attest. A memória privada é isolada por instalação no branch de evolução; confira os testes e o PR antes de considerar isso ativo na versão padrão. A memória associativa experimental é persistida como checkpoint separado. A sincronização do Blueprint precisa ser aprovada no painel do Render. O Postgres Free existente expira em 15/12/2026 e tem limite de 1 GB; é adequado para teste, não para dados permanentes. O serviço web Free pode dormir após 15 minutos sem tráfego e o SQLite local é efêmero.

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
- O runtime não usa chaves de provedores de IA externos.
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


## Autoevolução e pesquisa agendada

- `.github/workflows/ultron-autonomous-scout.yml` executa uma auditoria somente leitura a cada 10 minutos na branch padrão: coleta falhas recentes do Actions, issues abertas, marcadores de manutenção e pistas de repositórios públicos no GitHub. Não baixa nem executa código de terceiros.
- `.github/workflows/ultron-autonomous-evolution.yml` executa diariamente. Em PR, faz apenas smoke training isolado. Na branch padrão, continua a partir do último checkpoint BPE PT-BR validado e do mesmo tokenizer/corpus com splits fixos; se ainda não existir baseline, registra que está aguardando o pré-treinamento semanal em vez de treinar o corpus didático de 1,8 KB.
- `.github/workflows/ptbr-pretraining.yml` prepara corpus CC0 com manifesto/proveniência, treina tokenizer próprio e modelo do zero; os splits train/validation/test acompanham o artefato para permitir continuação diária comparável.
- `.github/workflows/ios-build.yml` gera um IPA arm64 sem assinatura diariamente para o SideStore. É preciso assinar e testar no iPhone.
- GitHub schedules só são ativados na branch padrão e são best-effort. PRs em rascunho não ativam os agendamentos.
- Checkpoints são experimentais. A perda de próximo token não comprova qualidade de conversa; o modelo ainda não é um LLM geral nem substitui o chat de produção.
- A automação não faz merge, deploy, publicação ou troca de pesos de produção. Alterações de código passam por branch, testes, PR e revisão.
