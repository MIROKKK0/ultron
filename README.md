# ULTRON

Assistente pessoal em português, com app nativo para iPhone, API HTTPS, autenticação, memória persistente e IA opcional.

## Componentes

- App SwiftUI para iPhone (iOS 16+).
- Backend FastAPI.
- PostgreSQL em produção ou SQLite para desenvolvimento local.
- Autenticação Bearer por `ULTRON_API_TOKEN`.
- Google Gemini (`GOOGLE_API_KEY`) ou OpenAI (`OPENAI_API_KEY`).
- Testes Python e GitHub Actions para CI, simulador e IPA.
- Núcleo próprio de agente com planejamento, recuperação lexical de memórias, autoavaliação e propostas de melhoria supervisionadas.
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
- `POST /feedback` com avaliação de 1 a 5 e comentário opcional.
- `GET /feedback/summary`: média de avaliações armazenadas.

A memória do chat prioriza itens com maior correspondência lexical. Feedback melhora a avaliação e orientação futura do produto, mas não atualiza automaticamente os pesos do Gemini/OpenAI.

Para PostgreSQL, defina `DATABASE_URL`. Para ativar respostas inteligentes, defina `GOOGLE_API_KEY` (Gemini) ou `OPENAI_API_KEY`. O Gemini é a opção prevista para começar com o nível gratuito disponível na conta Google AI Studio; limites e disponibilidade dependem da conta e do modelo.

Nunca coloque chaves de provedor ou tokens em commits, no app ou em arquivos públicos. Cadastre-os como variáveis secretas no serviço de hospedagem.

## Hospedagem Render

O serviço configurado é:

- API: https://ultron-api-c5ae.onrender.com
- Região: Virginia
- Plano: Free
- Banco PostgreSQL: plano Free, com expiração indicada pelo Render em 15/12/2026.

O arquivo `render.yaml` conecta `DATABASE_URL` ao banco. A sincronização do Blueprint ainda precisa ser aprovada no painel do Render. Sem essa conexão, o serviço usa SQLite local, que não deve ser tratado como armazenamento permanente em hospedagem efêmera.

Cadastre `GOOGLE_API_KEY` ou `OPENAI_API_KEY` no Environment do serviço para habilitar o modelo. `ULTRON_API_TOKEN` já é configurado separadamente no ambiente do serviço.

## App iOS e IPA

O projeto Xcode é gerado com XcodeGen:

```bash
brew install xcodegen
xcodegen generate
open ULTRON.xcodeproj
```

O workflow `ULTRON iOS Build` compila para simulador e gera um IPA arm64 sem assinatura para o SideStore assinar no próprio iPhone. O IPA só estará disponível depois que o job `device-ipa` terminar com sucesso.

No app, abra Configurações e informe:
1. URL HTTPS da API.
2. Token Bearer do ULTRON.

Depois, instale o IPA pelo SideStore. A compilação de simulador não pode ser instalada diretamente no iPhone.

## Segurança

- As rotas de chat e memória exigem Bearer token.
- As chaves do provedor de IA ficam apenas no servidor.
- O ULTRON não executa comandos arbitrários nem contorna autenticação ou assinaturas.
- Ações externas ou irreversíveis exigem confirmação explícita.
