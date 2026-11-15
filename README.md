# ULTRON

Assistente pessoal em português com app nativo para iPhone, API HTTPS, memória persistente e núcleo FlyBrain obrigatório, com geração de linguagem online opcional e fallback local.

## Componentes

- App SwiftUI para iPhone (iOS 17+).
- Backend FastAPI.
- PostgreSQL em produção ou SQLite para desenvolvimento local.
- Chat, pesquisa e status públicos com limite básico por IP; sem token manual no iPhone. O chat público é temporariamente sem memória persistente para não expor dados entre instalações. Rotas administrativas e de memória continuam protegidas.
- Núcleo de controle obrigatório FlyBrain no backend; quando configurado, o servidor usa Groq/OpenRouter Free para geração de linguagem e o iPhone mostra essa resposta diretamente. Sem provedor online, o app pode usar Qwen3 0.6B Q4_K_M local via llama.cpp/Metal; sem ambos, usa a resposta segura do servidor.
- Pesquisa web sem chave via metabusca DDGS, com links para as fontes; testes Python e GitHub Actions para CI, simulador e IPA.
- Núcleo neural obrigatório (`backend/fly_brain.py`): microcircuito LIF local inspirado em dinâmica de neurônios da mosca, com atividade recorrente, estado curto e sinais de prioridade para planner/solver/critic; o ciclo cognitivo sempre passa por ele antes da camada de linguagem local ou hospedada.
- O microcircuito LIF reduzido (48 neurônios por padrão) é o núcleo de controle leve. A ponte real para o conectoma FlyWire FAFB v783 (~138.639 neurônios) já existe em `backend/flywire_runtime.py`, com testes e execução dos experimentos documentados; ela só fica ativa após instalar código, dados e dependências e habilitar `ULTRON_ENABLE_FULL_FLYWIRE=1` em um host com recursos suficientes. Não está habilitada no Render Free.
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
- `GET /brain/status`: diagnóstico sem caminhos internos do host, com disponibilidade real, arquivos/dependências ausentes, runtime carregado, estímulos suportados e limites da aprendizagem.
- `POST /brain/research`: pesquisa web sem chave, com limite público por IP e resultados com URLs.
- `POST /brain/perception` com `{"goal":"..."}`: ponte conservadora de linguagem para os únicos estímulos do simulador FlyWire já documentados: alimentação → `sugar` e locomoção → `p9`; outros pedidos são marcados como não mapeados e continuam no núcleo LIF leve.
- `POST /brain/run` com `{"goal":"..."}`: ciclo cognitivo com planejador, solucionador, crítico e síntese.
- `POST /brain/multitask` com `{"tasks":["...","..."]}`: até cinco tarefas independentes em paralelo.
- `POST /feedback` com avaliação de 1 a 5 e comentário opcional.
- `GET /feedback/summary`: média de avaliações armazenadas.

O chat público não lê nem grava memória/conversas compartilhadas até existir uma identidade segura por instalação. Rotas administrativas protegidas mantêm a memória persistente. No chat do iPhone, use `/self`, `/plan seu objetivo`, `/research sua pergunta` e `/calc 12*(3+4)`. O endpoint `/brain/run` usa o FlyBrain para priorizar as estratégias locais e gerar uma síntese determinística. No app iOS, o endpoint `/chat` devolve um `brain_context` sem dados privados: o FlyBrain sempre processa primeiro, e a geração linguística Qwen3 local usa esses sinais e o resultado do servidor como contexto. O modelo é opcional e baixado sob demanda pelo usuário; sem ele, o app mantém a resposta segura do backend. Use `/research sua pergunta` para pesquisar na internet; o ULTRON retorna trechos e links de fontes. A busca não usa LLM para sintetizar e pode falhar se o mecanismo de pesquisa bloquear o servidor. `/brain/multitask` aceita até cinco tarefas. Feedback explícito do usuário calibra apenas a prioridade de planner/solver/critic, com ajuste limitado a ±15% e limite de 10 avaliações por hora/IP. Isso não treina pesos do modelo de linguagem nem sinapses FlyWire. O módulo experimental de associação usa codificador esparso, recompensa e decaimento; seu estado é salvo no banco.

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

O projeto Xcode é gerado com XcodeGen. O app usa `swift-llama-cpp` (llama.cpp b11960) e requer iOS 17+; o workflow prepara o XCFramework oficial com checksum verificado e fatia de simulador antes de compilar:

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
- O FlyBrain consome a codificação e usa a recordação associativa como sinal limitado de atividade do grupo de memória.
- O feedback explícito no aplicativo atualiza apenas prioridades das estratégias, com limites; não modifica o conectoma FlyWire ou os pesos de um LLM.
- Isso é uma camada computacional inspirada em aprendizagem biológica, não uma reprodução completa do mushroom body nem prova de inteligência geral.


## Geração de linguagem online (opcional, com fallback local)

O chat continua executando o FlyBrain antes de qualquer decodificador. Quando credenciais são configuradas no ambiente do backend, a camada de linguagem pode usar provedores OpenAI-compatible em uma ordem controlada; se todos falharem ou atingirem suas cotas, o backend retorna ao decodificador local. O app iOS usa a resposta online diretamente e só executa o Qwen local quando o backend informa que a geração foi local.

Configuração no painel de hospedagem (nunca no app, no repositório ou em commits):

- `GROQ_API_KEY`: chave da conta Groq. Modelo padrão: `openai/gpt-oss-20b`.
- `OPENROUTER_API_KEY`: chave OpenRouter. Modelo padrão: `openrouter/free`, que seleciona apenas modelos gratuitos.
- `ULTRON_AI_PROVIDER_ORDER`: opcional; ordem separada por vírgulas, padrão `groq,openrouter`.
- `GROQ_MODEL` ou `OPENROUTER_MODEL`: não altere para modelos pagos sem entender a cobrança. Modelos diferentes dos padrões são bloqueados, a menos que `ULTRON_ALLOW_PAID_AI=1` seja explicitamente configurado.
- `GET /ai/status`: informa provedores configurados sem revelar chaves.

A implementação não cria contas nem chaves e não ativa cobrança. Os planos gratuitos continuam sujeitos a limites por minuto, tokens e dia; quando as cotas acabam, o ULTRON tenta o próximo provedor configurado e depois usa o fallback local. Isso melhora a disponibilidade, mas não é uso ilimitado. O chat público continua sem memória compartilhada e não envia histórico privado ao provedor. Cada solicitação online envia apenas a mensagem atual e sinais de controle não privados do FlyBrain.

Provedores de referência e limites oficiais:
- Groq: https://console.groq.com/docs/rate-limits e https://console.groq.com/docs/models
- OpenRouter Free: https://openrouter.ai/collections/free-models
