# ULTRON — capacidades nativas do iPhone

## Implementado nesta branch
- Copiar respostas para a área de transferência.
- Ouvir respostas em português brasileiro e interromper a leitura.
- Compartilhar respostas pelo painel nativo do iOS.
- Perguntar ao ULTRON por uma ação do app Atalhos/Siri, iniciada pelo usuário.
- Monitor holográfico procedural com estados de conexão, processamento, resposta e erro.
- Eventos SSE do backend para que os estados de processamento/resposta não sejam inventados pela interface.

## Referência visual
A inspiração é o holograma azul de ULTRON em *Vingadores: Era de Ultron*: geometria angular, anéis, partículas e reorganização de energia. A implementação é original e leve; não reutiliza imagens, modelos 3D ou assets do filme.

## Limites do iOS
ULTRON é um app comum. Não pode controlar silenciosamente outros apps, ler dados arbitrários, ignorar a tela bloqueada, executar shell arbitrário ou contornar permissões. Use App Intents/Atalhos e APIs públicas, com confirmação para ações sensíveis.

## Segurança
- Não inserir segredo global do servidor dentro do IPA.
- Não executar ações recebidas do backend sem uma interação explícita do usuário.
- Pedir apenas permissões necessárias e tratar negação/cancelamento.
- Não usar Accessibility hacks para automatizar outros apps.

## Monitor cerebral
O monitor usa Canvas e TimelineView, com 28 partículas limitadas e 12 FPS em espera / 24 FPS durante requisições. O endpoint SSE comunica apenas os estados externos do pedido. Isso não representa ativações internas do classificador ou do Transformer e não implica consciência.
