# ULTRON Tiny — Transformer generativo experimental

Implementação pequena de Transformer decoder-only, com pesos inicializados do zero.
Sem modelo pré-treinado, provedor externo ou tokenizer de terceiros.

## Componentes
- Tokenizador UTF-8 byte-level versionado (`ultron-byte-v1`).
- Atenção causal via `scaled_dot_product_attention`, sem criar máscara LxL manual.
- Treino CPU reproduzível com AdamW e clipping de gradiente.
- Divisão sequencial de treino/validação antes de extrair janelas.
- Loss e perplexidade de validação nos logs e metadados do checkpoint.
- Escrita atômica do checkpoint para evitar artefatos incompletos.

## Treinar
```bash
python -m pip install -r training/generative/requirements.txt
python -m training.generative.train --steps 1000
```

O artefato fica em `artifacts/ultron-tiny.pt`. O backend de produção continua
usando o classificador de intenções e fallback determinístico até o modelo
generativo passar por avaliação independente e benchmark de memória.

## Limites
O corpus atual é pequeno e didático. O modelo não tem conhecimento geral e não
equivale ao ChatGPT. Não treinar no serviço web de 512 MB. Antes de integrar,
medir qualidade em português, segurança, latência, RSS e carga concorrente.


## Melhorias recentes de treino e geração
- Janelas de próximo token são amostradas por indexação vetorizada, reduzindo overhead Python.
- Scheduler de taxa de aprendizado com warmup curto e decaimento cosseno.
- Geração permite modo greedy (padrão) ou sampling reproduzível com temperatura e top-k.
- Checkpoint registra tamanho do corpus e parâmetros de agenda de aprendizagem.

Essas mudanças melhoram o pipeline, não a capacidade por si só. O corpus atual continua didático e pequeno; qualquer saída do Tiny GPT continua experimental e não deve substituir o decodificador/skills de produção sem avaliação.


## BPE próprio e avaliação comparável

A linha BPE (ultron-bpe-v1) é treinada apenas no split de treino do corpus licenciado. O checkpoint registra versão/hash do tokenizador e tamanho do vocabulário; o treino seleciona o melhor estado pela validação e avalia o teste separado apenas após a seleção. Perplexidade é útil dentro da mesma tokenização, mas não deve ser comparada diretamente entre tokenizadores. Por isso, o pipeline também calcula bits-per-byte (BPB), uma métrica normalizada pelo tamanho UTF-8 do texto. BPB ainda mede apenas previsão do próximo token: não prova qualidade de diálogo, factualidade, segurança ou uso de ferramentas.

O corpus dataseek/ptbr-books-publicos declara CC0-1.0 e contém livros de domínio público. A própria ficha informa que a fonte não foi sanitizada de PII e pode conter nomes, contatos ou conteúdo enviesado; a limpeza por regex do ULTRON é apenas uma mitigação incompleta. Não publique amostras/checkpoints com dados suspeitos sem revisão adicional.
