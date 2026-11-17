# ULTRON

Assistente pessoal em português com app nativo para iPhone, API HTTPS e memória persistente, sem simulação neural experimental e sem API externa de IA.

## Componentes

- App SwiftUI para iPhone (iOS 16+).
- Backend FastAPI.
- PostgreSQL em produção ou SQLite para desenvolvimento local.
- Chat, pesquisa e status públicos com limite básico por IP; sem token manual no iPhone. O chat público é temporariamente sem memória persistente para não expor dados entre instalações. Rotas administrativas e de memória continuam protegidas.
- Decodificador linguístico local determinístico; não exige tokens Gemini, OpenAI ou Claude.
- Pesquisa web sem chave via metabusca DDGS, com links para as fontes; testes Python e GitHub Actions para CI, simulador e IPA.
- Feedback persistido para medir satisfação ao longo do tempo (não treina pesos do modelo).

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
- `GET /brain/status`: estado da orquestração local, especialistas e limites do decodificador.
- `POST /brain/research`: retorna 503 até existir uma implementação de pesquisa local sem serviços externos.
- `POST /brain/run` com `{"goal":"..."}`: ciclo cognitivo com planejador, solucionador, crítico e síntese.
- `POST /brain/multitask` com `{"tasks":["...","..."]}`: até cinco tarefas independentes em paralelo.
- `POST /feedback` com avaliação de 1 a 5 e comentário opcional.
- `GET /feedback/summary`: média de avaliações armazenadas.

O chat público não lê nem grava memória/conversas compartilhadas até existir uma identidade segura por instalação. Rotas administrativas protegidas mantêm a memória persistente. No chat do iPhone, use `/self`, `/plan seu objetivo`, `/research sua pergunta` e `/calc 12*(3+4)`. O endpoint `/brain/run` executa planner, solver e critic locais e gera uma síntese determinística. Use `/research sua pergunta` para pesquisar na internet; o ULTRON retorna trechos e links de fontes. A busca não usa LLM para sintetizar e pode falhar se o mecanismo de pesquisa bloquear o servidor. `/brain/multitask` aceita até cinco tarefas. Feedback explícito do usuário calibra apenas a prioridade de planner/solver/critic, com ajuste limitado a ±15% e limite de 10 avaliações por hora/IP. Isso não treina pesos do modelo de linguagem. O módulo experimental de associação usa codificador esparso, recompensa e decaimento; seu estado é salvo no banco.

Para PostgreSQL, defina `DATABASE_URL`. Nenhuma chave de provedor de IA é necessária. O chat e a pesquisa públicos têm limites por IP; memória e rotas administrativas continuam exigindo `ULTRON_API_TOKEN`.

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

O workflow `ULTRON iOS Build` compila para simulador e gera um IPA arm64 sem assinatura para o SideStore assinar no próprio iPhone. O IPA só estará disponível depois que o job `device-ipa` terminar com sucesso.

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
