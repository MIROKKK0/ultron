# ULTRON Memory
Os dados reais ficam no banco SQLite local (~/.ultron/core.db, configurável por ULTRON_CORE_DB).
- Identidade não pertence ao modelo.
- Conversas, fatos, relações, skills, tarefas, endpoints MCP e avaliações são persistidos.
- Memória deve ser auditável e exportável.
- Nunca salvar chaves, tokens, senhas ou segredos nesta memória.
