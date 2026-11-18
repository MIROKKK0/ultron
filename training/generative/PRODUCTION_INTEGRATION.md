# Integração do Transformer próprio no ciclo cognitivo

O ULTRON Tiny participa como especialista experimental. O candidato e suas métricas
são expostos no ciclo, mas não substituem automaticamente o Gemini.

Ativação controlada: ULTRON_TINY_ENABLED=true e ULTRON_TINY_CHECKPOINT=artifacts/ultron-tiny.pt.
Para BPE, configure ULTRON_TINY_TOKENIZER_JSON. Limite de geração: 96 tokens.

Treine fora do serviço web de 512 MB. Loss, perplexidade e bits-per-byte medem
previsão do próximo token, não qualidade de diálogo. Antes de promover o modelo,
avalie diálogos retidos, relevância, factualidade, segurança, latência e RSS.
Feedback deve ser associado a uma resposta e registrado como avaliação; não
deve alterar pesos automaticamente. A promoção exige revisão humana.