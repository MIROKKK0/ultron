# Ultron — IA Pessoal Avançada

IA pessoal poderosa, estilo ChatGPT, com memória persistente, ferramentas, auto-aperfeiçoamento e capacidade de interagir com outras IAs.

absolute olliE.

## Capacidades

- **Conversasção natural** — Interface CLI estilo ChatGPT
- **Memória de longo prazo** — Lembra preferências, fatos e contexto do usuário (SQLite)
- **Ferramentas**:
  - Busca web (DuckDuckGo)
  - Calculadora
  - Salvar/recuperar memória
  - Gerar prompts otimizados para outras IAs (Claude, Gemini, Grok, etc.)
  - Auto-aperfeiçoamento (atualiza o próprio system prompt)
- **Multi-provedor** — Funciona com OpenAI, OpenRouter, Groq, Together, etc.
- **Auto-evolutivo** — Analisa interações e melhora seu próprio comportamento

## Setup

```bash
# 1. Clone e entre no diretório
git clone https://github.com/MIROKKK0/ultron.git
cd ultron

# 2. Instale dependências
pip install -r requirements.txt

# 3. Configure a API
cp .env.example .env
# Edite o .env e coloque sua chave
```

### Arquivo .env

```env
OPENAI_API_KEY=sk-...
# Opcional: use OpenRouter, Groq, etc.
# OPENAI_BASE_URL=https://openrouter.ai/api/v1
# ULTRON_MODEL=anthropic/claude-sonnet-4
# ULTRON_MODEL=gpt-4o
```

## Uso

```bash
python ultron.py
```

### Comandos especiais

- `sair` / `exit` / `quit` — Encerra
- `melhorar` — Força auto-aperfeiçoamento (analisa conversas e atualiza system prompt)

## Arquitetura

- `ultron.py` — Agente principal com loop de ferramentas
- Memória em `~/.ultron/memory.db` (SQLite)
- System prompt em `~/.ultron/system_prompt.txt` (editável e auto-atualizável)

## Melhorias futuras possíveis

- Interface web (Streamlit/Gradio)
- Voz (Whisper + TTS)
- Mais ferramentas (arquivo, código, calendário)
- Integração com MCP
- RAG com documentos pessoais
- Multi-agente (especialistas)

absolute olliE pro Sam.
