# ULTRON — pesquisa técnica e plano de evolução do núcleo

Atualizado em 17/11/2026. Este documento separa o que já existe no repositório do que ainda precisa ser implementado e medido.

## Diagnóstico real do código

- O roteador de intenção é um classificador Naive Bayes próprio, com n-gramas de bytes/palavras, 4.096 buckets e 225 exemplos anotados. É rápido e leve, mas não gera texto aberto.
- O núcleo experimental é um Transformer decoder-only com 118.144 parâmetros, tokenizer UTF-8 byte-level de 258 símbolos e pesos aleatórios no início do treino.
- O corpus generativo atual é didático e muito pequeno. Um treino curto valida o pipeline, não ensina conhecimento geral.
- O backend de produção continua usando o classificador e as habilidades determinísticas. O Transformer não deve ser conectado ao chat até passar por avaliação independente.
- O servidor Render de 512 MB deve hospedar roteamento, ferramentas e respostas curtas; treino de pesos não deve rodar dentro do serviço web.
- O iPhone agora envia contexto recente limitado por requisição; memória persistente por instalação continua sendo uma tarefa separada e requer identidade segura.

## Pesquisa e referências

1. **Atenção eficiente:** PyTorch SDPA escolhe kernels otimizados conforme dispositivo e formato; manter atenção causal e medir CPU real, não presumir aceleração.  
   https://docs.pytorch.org/tutorials/intermediate/scaled_dot_product_attention_tutorial
2. **Qualidade de dados em SLMs:** revisão sistemática de 2026 discute filtragem, deduplicação, limpeza e construção de conjuntos de alta qualidade. Para um modelo pequeno, ruído e repetição ocupam uma fração grande da capacidade.  
   https://onlinelibrary.wiley.com/doi/full/10.1111/exsy.70331
3. **Core ML:** a Apple documenta execução em CPU, GPU e Neural Engine, com foco em memória, consumo e privacidade; permite converter modelos próprios com Core ML Tools.  
   https://developer.apple.com/documentation/coreml
4. **Compressão:** Core ML Tools descreve quantização e paletização para reduzir tamanho, latência e consumo, sempre medindo a perda de qualidade.  
   https://github.com/apple/coremltools/blob/main/docs-guides/source/opt-overview.md
5. **Transformers:** os tutoriais oficiais do PyTorch cobrem SDPA, Nested Tensors e torch.compile; o ganho depende da forma do modelo e do hardware.  
   https://docs.pytorch.org/tutorials/intermediate/transformer_building_blocks.html
6. **Treino de GPT do zero:** material de Andrej Karpathy para compreender tokenizer, atenção, treino e validação. É referência didática, não uma promessa de que um modelo pequeno reproduzirá um GPT grande.  
   https://www.youtube.com/watch?v=kCc8FmEb1nY

## Melhorias feitas nesta etapa

- Amostragem vetorizada de janelas de próximo token, evitando construir cada batch com loops Python.
- Scheduler de taxa de aprendizado com warmup e decaimento cosseno.
- Geração greedy por padrão e sampling opcional com temperatura/top-k e semente reproduzível.
- Metadados do checkpoint incluem tamanho do corpus e configuração de learning rate.
- Testes de alinhamento input/target, reprodutibilidade, split e restauração do modo train/eval.

## Próximas etapas em ordem segura

### P0 — Dados e avaliação
- Construir corpus português com licença e origem registradas, filtragem de qualidade e deduplicação exata/fuzzy.
- Separar treino/validação/teste por documento ou origem, não apenas por janela aleatória.
- Criar benchmark fixo de português: compreensão, cálculo, instruções, contexto, factualidade, recusa e tool calling.
- Comparar baseline antes/depois; rejeitar checkpoint que não melhore métricas sem piorar segurança.

### P1 — Tokenização e arquitetura
- Medir bytes por caractere e comprimento de sequência no corpus PT.
- Treinar um tokenizer BPE próprio no corpus selecionado e versionar merges/vocabulário junto dos pesos.
- Comparar RoPE versus embeddings posicionais, RMSNorm versus LayerNorm e tied embeddings, sempre por ablação.
- Não aumentar parâmetros até os dados e métricas justificarem.

### P2 — Treino e inferência
- Usar checkpoints, retomada de treino, early stopping por validação e clipping.
- Avaliar quantização FP16/INT8/INT4 no caminho de exportação; comparar tamanho, latência e qualidade.
- Exportar para Core ML apenas depois de congelar arquitetura e criar testes equivalentes PyTorch/Core ML.
- Medir no iPhone 11 Pro: latência do primeiro token, tokens/s, pico de memória, temperatura e bateria.

### P3 — Agente e autoevolução
- Ciclo seguro: observar erro → abrir issue → propor patch em branch → rodar testes/benchmarks → revisão humana → merge.
- Skills devem ter contrato de entrada/saída, permissões mínimas, timeout e testes.
- Feedback do usuário só ajusta prioridades limitadas; não deve alterar pesos nem publicar código sozinho.
- Toda versão do modelo precisa de hash do corpus, tokenizer, config, métricas e checkpoint reversível.

## Critério de honestidade

Um Transformer com 118 mil parâmetros e corpus pequeno não é um assistente geral. O objetivo imediato é aprender tarefas estreitas e verificáveis, melhorar o roteamento e preparar um caminho de treino realista. Não chamar de "treinado" ou "inteligente" apenas porque a loss diminuiu ou o arquivo foi salvo.
