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

Escolha um provedor sem alterar o núcleo ou a memória. Para Gemini:

```env
ULTRON_PROVIDER=gemini
GEMINI_API_KEY=sua_chave
GEMINI_MODEL=gemini-2.5-flash
```

Também há adaptadores `openai`, `openrouter` e `custom` (API compatível com OpenAI). Veja `.env.example`.

## Uso

```bash
python ultron.py
```

### Comandos especiais

- `sair` / `exit` / `quit` — Encerra
- `melhorar` — Força auto-aperfeiçoamento (analisa conversas e atualiza system prompt)

## Arquitetura

- `ultron.py` — interface e loop de ferramentas
- `ultron_core/provider.py` — adaptador de modelo substituível
- `ultron_core/governance.py` — regras determinísticas de aprovação
- `ultron_core/orchestrator.py` — validação de caminhos e execução limitada de testes
- Memória em `~/.ultron/memory.db` (SQLite), independente do provedor
- Identidade em `~/.ultron/system_prompt.txt`, independente do provedor
- `ARCHITECTURE.md` — fronteiras de propriedade e fluxo de evolução

O modelo conectado propõe; ULTRON controla memória, execução, testes e critérios. Testes verdes liberam uma alteração para revisão por PR, nunca publicação direta automática.

## Melhorias futuras possíveis

- Interface web (Streamlit/Gradio)
- Voz (Whisper + TTS)
- Mais ferramentas (arquivo, código, calendário)
- Integração com MCP
- RAG com documentos pessoais
- Multi-agente (especialistas)

absolute olliE pro Sam.
