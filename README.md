# ULTRON

Assistente pessoal em português, com API HTTP, memória persistente local e integração opcional com um modelo de IA.

## O que existe nesta versão

- API FastAPI com endpoint de saúde e conversa.
- Memória persistente SQLite: criar, listar e apagar notas.
- Calculadora com parser restrito (sem executar código arbitrário).
- Integração opcional com OpenAI Responses API.
- Resposta local básica quando não há chave de IA configurada.
- Testes automatizados e CI no GitHub Actions.

## Executar

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Abra `http://localhost:8000/docs` para testar a API.

## Comandos de conversa

- `/help` — mostra os comandos disponíveis.
- `/remember texto` — grava uma nota na memória local.
- `/calc 12*(3+4)` — calcula uma expressão matemática segura.
- `GET /memory` — lista as notas.
- `DELETE /memory/{id}` — apaga uma nota.

## Inteligência artificial opcional

Defina `OPENAI_API_KEY` no ambiente do servidor. Opcionalmente, defina `ULTRON_MODEL`. Nunca coloque chaves no código, no README ou em commits.

Sem a chave, o serviço continua funcionando com comandos locais básicos.

## Segurança

Esta base não executa comandos arbitrários, não tenta invadir sistemas e não contorna autenticação ou assinaturas. Ações externas e irreversíveis devem exigir confirmação explícita.

## Estado do projeto

Esta é a fundação do backend. A interface iOS, voz, permissões nativas e distribuição IPA ainda precisam ser implementadas e validadas separadamente.
