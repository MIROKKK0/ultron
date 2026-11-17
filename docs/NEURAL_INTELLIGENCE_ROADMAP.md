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


## Implementação iniciada nesta evolução

- O app iOS possui monitor holográfico procedural com partículas e núcleo
  geométrico, desenhado por `Canvas` + `TimelineView`.
- O endpoint `POST /chat/stream` envia eventos reais de processamento e
  resposta; o cliente iOS acompanha esses eventos via Server-Sent Events.
- O pacote `training/` contém um tokenizador byte-level próprio e um
  Transformer causal pequeno, com inicialização aleatória e treino reproduzível.
- O corpus inicial é autoral e serve apenas para smoke training.
- O runtime web expõe `GET /runtime/status` para medir RSS e pressão contra
  orçamento configurável de 512 MB.
- O iOS oferece cópia, leitura em voz alta, compartilhamento e uma ação
  invocável pelo app Atalhos/Siri.

## O que ainda não está concluído

- Nenhum checkpoint treinado e avaliado está integrado ao backend.
- O modelo experimental ainda não tem qualidade de conversa geral.
- A API online e o streaming precisam de validação no deploy real.
- A IPA precisa concluir build e ser testada no iPhone físico.
- Memória pessoal por instalação ainda precisa de identidade/autorização segura.
- A animação é um monitor visual de estados do ciclo, não leitura de ativações
  internas de uma rede neural nem prova de consciência.
