# iOS — identidade privada e memória v2

## Fluxo de instalação

1. O app cria um UUID de instalação e um segredo aleatório local.
2. Os dois valores são guardados no Keychain com `ThisDeviceOnly`; nenhum token administrativo do Render/GitHub é embutido no IPA.
3. O app registra a identidade em `POST /v2/installations/register`. O backend aplica rate limit e persiste somente o SHA-256 do segredo.
4. As chamadas autenticadas enviam `X-Installation-ID` e `X-Installation-Token` por HTTPS.

## Rotas usadas pelo app

- `POST /v2/brain/run`: executa o ciclo cognitivo com histórico recente limitado e memórias da instalação autenticada.
- `POST /v2/memory`: salva memória episódica, semântica ou procedural.
- `GET /v2/memory`: lista apenas as memórias da instalação.
- `DELETE /v2/memory/{id}`: apaga uma memória pertencente à instalação.

Os comandos de chat `/remember texto`, `/remember episodic texto`, `/remember semantic texto`, `/remember procedural texto`, `/memories` e `/forget ID` usam as rotas v2.

## Limites e segurança

- O segredo nunca é enviado a um modelo generativo nem gravado em telemetria.
- O servidor guarda hash do segredo, não o segredo em texto puro.
- O endpoint de registro é público por necessidade de primeiro uso, mas limitado por IP e idempotente para o mesmo par ID/segredo.
- Uma instalação não pode substituir o segredo de outra instalação com o mesmo ID.
- A rota antiga de chat permanece como fallback se o backend implantado ainda não oferecer `/v2/brain/run`; nesse caso, a memória tipada não é usada até o deploy do backend v2.
- A IPA do GitHub é unsigned e deve ser assinada pelo SideStore.

## Aceite

CI precisa validar isolamento, idempotência, rejeição de credencial conflitante, histórico limitado e ausência de acesso sem credencial. O workflow iOS deve compilar simulador e IPA arm64.