# Memória privada por instalação

## Contrato

- `POST /installations/register` cria uma identidade aleatória e devolve uma credencial aleatória uma única vez.
- O servidor persiste apenas SHA-256 da credencial; o texto do token não é salvo.
- O app deve guardar a credencial no iOS Keychain (classe `kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly` ou mais restritiva compatível com o fluxo).
- `POST /memory`, `GET /memory` e `DELETE /memory/{id}` exigem `Authorization: Bearer <installation-token>`.
- Toda leitura e exclusão filtra por `installation_id` no banco. Conhecer o ID numérico de outra instalação não concede acesso.
- `DELETE /installation` revoga a credencial e apaga somente as memórias dessa instalação.
- Registro é limitado por IP a 10 por hora por processo. Produção com múltiplas instâncias deve usar rate limit compartilhado (Postgres/Redis) antes de abrir o registro amplamente.

## Migração e compatibilidade

A tabela legada `memories` não é exposta por essas rotas novas e não é atribuída automaticamente a nenhuma instalação. Isso evita que o primeiro telefone que se registrar herde dados antigos compartilhados. Os registros legados permanecem intactos para uma migração explícita e revisada.

As tabelas `installations` e `installation_memories` são criadas na inicialização. SQLite e PostgreSQL são suportados. O backend nunca envia a credencial compartilhada `ULTRON_API_TOKEN` para o aplicativo.

## Próxima integração iOS

O backend está preparado, mas o app iOS ainda precisa:
1. registrar a instalação uma vez;
2. persistir o token no Keychain, sem UserDefaults nem logs;
3. adicionar telas/ações de lembrar, listar e apagar;
4. enviar o token somente nas rotas `/memory`;
5. apagar token local quando a instalação for revogada;
6. testar reinstalação, restauração, perda de rede e token revogado.

Não afirmar que a memória pessoal está pronta no iPhone até essa integração e os testes físicos serem concluídos.
