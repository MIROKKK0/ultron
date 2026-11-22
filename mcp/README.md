# MCP — conexão real e ferramentas externas

O núcleo ULTRON mantém sua identidade e memória independentes dos servidores MCP.

## Conexão HTTP

O cliente `mcp/client.py` implementa o fluxo MCP Streamable HTTP:
1. handshake `initialize` com versão de protocolo e identificação ULTRON;
2. notificação `notifications/initialized`;
3. sessão persistente via `Mcp-Session-Id`;
4. descoberta por `tools/list`;
5. chamada por `tools/call`;
6. encerramento da sessão quando o cliente fecha.

Configuração:
- Registre um endpoint HTTPS em `UltronCore.register_mcp_server`.
- Defina `ULTRON_MCP_TOKEN` no ambiente do processo, nunca no repositório.
- Habilite explicitamente o servidor depois de verificar o endpoint e as permissões.
- No chat, use `ultron_core` com `mcp_discover` e `mcp_call`.

O token não é gravado no SQLite nem incluído nos logs. A conexão só é considerada válida depois de um handshake e uma resposta real de `tools/list`. A descoberta não significa que toda ferramenta remota seja segura ou autorizada para qualquer tarefa.

## Estado de validação

O cliente e testes com respostas simuladas foram adicionados. Ainda falta validar contra um servidor MCP real com credenciais configuradas no ambiente de execução do ULTRON. Nenhum endpoint ou token de produção foi inventado.
