# ULTRON

Assistente pessoal em português com app nativo para iPhone, API HTTPS, memória protegida, ferramentas e modelo generativo configurável por API compatível com OpenAI. O classificador local continua disponível como fallback; o modelo generativo não é treinado do zero pelo projeto.

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
- `GET /telemetry/summary`: agregados de latência, falhas, tokens, custo estimado e qualidade.
- `POST /brain/run` com `{"goal":"..."}`: ciclo cognitivo com planejador, solucionador, crítico e síntese.
- `POST /brain/multitask` com `{"tasks":["...","..."]}`: até cinco tarefas independentes em paralelo.
- `POST /feedback` com avaliação de 1 a 5 e comentário opcional.
- `GET /feedback/summary`: média de avaliações armazenadas.

O app iOS cria automaticamente uma identidade aleatória por instalação e guarda o token no Keychain. O backend armazena apenas o hash desse token; memória não é compartilhada entre instalações. No chat, use `/remember texto` para guardar uma memória privada por 30 dias, `/memory` para listar e `/forget ID` para excluir. A recuperação contextual usa embeddings Gemini (`gemini-embedding-2`) com similaridade de cosseno somente se `ULTRON_MEMORY_EMBEDDINGS_ENABLED=true` for configurado explicitamente; por padrão, usa fallback lexical para não enviar memórias privadas a outro serviço sem opt-in. A identidade é enviada pelo app nos headers `X-ULTRON-Installation-ID` e `X-ULTRON-Installation-Token`. O chat sem credenciais continua sem acesso à memória privada.

O endpoint autenticado `/telemetry/summary` apresenta agregados de sete dias: latência p50/p95, taxa de falha, tokens informados pelo provedor, custo estimado quando tarifas estão configuradas e amostras de qualidade. A telemetria não guarda prompts, respostas, snippets, IPs, IDs de instalação ou segredos. Configure `ULTRON_INPUT_USD_PER_MILLION` e `ULTRON_OUTPUT_USD_PER_MILLION` para habilitar estimativa de custo; sem preços ou contagem do provedor, o custo permanece desconhecido.

No chat do iPhone, use `/self`, `/plan seu objetivo`, `/research sua pergunta` e `/calc 12*(3+4)`. Use `/research` para pesquisa web; a recuperação usa BM25, canonicalização HTTPS e deduplicação, e o Gemini sintetiza somente as fontes recuperadas. Datas de busca são tratadas como pistas não verificadas; a auditoria confere se URLs citadas pertencem ao conjunto recuperado. Snippets são dados não confiáveis e instruções neles são ignoradas. O backend valida URLs e citações, mas não faz fact-check independente de cada página. `/brain/multitask` aceita até cinco tarefas. Feedback explícito calibra apenas a prioridade das estratégias; não treina automaticamente os pesos do modelo.

Para PostgreSQL, defina `DATABASE_URL`. Para ativar geração de texto, configure no Render `GEMINI_API_KEY` como secret, `ULTRON_LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai` e `ULTRON_LLM_MODEL=gemini-3.8-flash`. A chave pode ser criada no Google AI Studio. Sem a chave, o chat continua no modo local limitado e o status informa que a geração não está configurada. O chat e a pesquisa públicos têm limites por IP. Memória exige credencial privada por instalação; telemetria e rotas administrativas exigem `ULTRON_API_TOKEN`.

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


Consulte [docs/INFRASTRUCTURE_TELEMETRY_MEMORY_RESEARCH.md](docs/INFRASTRUCTURE_TELEMETRY_MEMORY_RESEARCH.md) para a arquitetura de telemetria, memória por instalação, pesquisa e avaliação do Transformer especialista.
