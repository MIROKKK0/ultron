# MCP — integrações externas
O núcleo mantém registro persistente de servidores MCP (nome, endpoint, transporte e estado habilitado), sem acoplar identidade ou memória a um servidor específico.
- Registre endpoints HTTP(S) via UltronCore.register_mcp_server.
- Credenciais devem vir de variáveis de ambiente/secret manager, nunca do Git.
- Antes de habilitar execução, implemente autenticação, descoberta real de tools, timeout, logs sem segredos e validação de permissões.
- Registro não significa conexão: health check, sessão e descoberta reais ainda precisam ser validados.
