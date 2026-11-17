# ULTRON — roteiro de evolução próprio

## Estado atual

O backend usa FastAPI, memória persistente, pesquisa web e especialistas locais
(planner, solver e critic). O decodificador de conversa ainda é determinístico;
ele não é um modelo de linguagem treinado.

FlyBrain e o runtime FlyWire foram retirados da arquitetura ativa. Nenhuma etapa
do chat depende de simulação neural, conectoma externo ou dados de terceiros.
Também não há chamadas a provedores de IA hospedados.

## Direção técnica

1. Criar tokenizer próprio e versionado, inicialmente byte-level para cobrir
   português e qualquer entrada UTF-8 sem depender de vocabulário externo.
2. Implementar uma arquitetura Transformer decoder-only original, com pesos
   inicializados aleatoriamente e código de treino reproduzível.
3. Construir corpus próprio/licenciado, com deduplicação, filtros de qualidade,
   documentação da origem e remoção de dados pessoais.
4. Treinar e avaliar em hardware compatível; não declarar o modelo capaz antes
   de medir perda, perplexidade, qualidade em português, segurança e latência.
5. Exportar checkpoints versionados e servir o modelo por API própria.
6. Integrar o app iOS à API ULTRON, sem chave de provedor externo embutida no IPA.

## Limites e critérios

- O decodificador atual é uma interface determinística e não deve ser anunciado
  como IA generativa avançada.
- Treinar do zero exige dados e computação. GitHub Actions gratuito pode validar
  código e executar testes pequenos, mas não substitui treinamento GPU em escala.
- Cada etapa deve ficar em branch isolada, passar CI e revisão antes de merge.
- O backend deve continuar funcional quando o checkpoint do modelo estiver
  ausente, informando claramente que o modelo ainda não está treinado.
- Nenhuma alteração deve prometer qualidade equivalente a modelos grandes sem
  benchmarks reproduzíveis.


## Implementação iniciada — monitor, treino e iPhone

- O app iOS desenha o holograma por Canvas/TimelineView e acompanha eventos SSE
  reais do ciclo de requisição.
- `POST /chat/stream` transmite estados de processamento e resposta.
- O app inclui copiar, fala pt-BR, parar leitura, compartilhar e uma ação
  Atalhos/Siri iniciada pelo usuário.
- O classificador de intenções próprio já existente foi preservado.
- `training/generative/` contém um segundo protótipo experimental: tokenizador
  byte-level próprio, Transformer causal com pesos aleatórios, corpus autoral e
  treinamento CPU reproduzível. Nenhum checkpoint foi treinado ou integrado
  nesta mudança.
- `GET /runtime/status` mede RSS e pressão sobre o orçamento de 512 MB.

## Pendências obrigatórias

- O protótipo generativo não tem qualidade geral e não substitui o classificador
  existente; precisa de corpus amplo, avaliação e benchmark antes de produção.
- A API e o streaming precisam ser testados no deploy ativo.
- A IPA deve compilar, ser empacotada e testada no iPhone físico.
- A memória pessoal precisa de identidade segura por instalação.
- O monitor representa estados externos do pedido, não ativações internas da rede
  nem consciência.
