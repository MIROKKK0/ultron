# ULTRON — estratégia de dados em português e orçamento de treino

Atualizado em 17/11/2026. Nenhum corpus externo foi copiado para o repositório nesta etapa; as fontes abaixo foram avaliadas para uma futura ingestão rastreável.

## Diagnóstico quantitativo atual

- Corpus generativo versionado: 1.823 caracteres/bytes UTF-8 e 24 linhas.
- Tokenizer atual: byte-level, 258 símbolos incluindo BOS/EOS.
- Transformer: 118.144 parâmetros.
- Referência aproximada de planejamento Chinchilla: 20 tokens por parâmetro, ou ~2.362.880 tokens para 118.144 parâmetros. É uma heurística derivada de estudos de escala, não uma lei universal nem garantia de qualidade.
- O corpus atual tem aproximadamente 1.300 vezes menos unidades byte-token que essa referência, e é didático/repetitivo. O perplexity muito alto no smoke test é esperado; dez passos só provam que o código roda.

## Fontes de corpus PT-BR avaliadas

### 1. dataseek/ptbr-wiki
https://huggingface.co/datasets/dataseek/ptbr-wiki

- Dataset card informa 1.084.716 artigos PT-BR, ~581,25 milhões de tokens estimados e ~1,46 GB Parquet comprimido.
- Licença CC BY-SA 4.0, herdada da Wikipedia; derivados precisam respeitar compatibilidade ShareAlike e atribuição.
- O card informa explicitamente que não houve limpeza de PII nem filtro de segurança abrangente.
- É a opção mais interessante para um primeiro experimento de pré-treino em português, mas precisa de amostragem, deduplicação, filtros e trilha de atribuição.
- Não baixar o dataset inteiro para o Git. Fazer streaming e limitar o experimento a um orçamento definido.

### 2. dataseek/ptbr-books-publicos — melhor candidato para o primeiro piloto
https://huggingface.co/datasets/dataseek/ptbr-books-publicos

- Dataset card informa 28.245 segmentos de livros brasileiros em domínio público, ~213 MB e licença CC0 1.0.
- Streaming é suportado; o material vem de arquivos públicos, foi filtrado por tipo/idioma e é descrito como redistribuível.
- O card também alerta que não houve remoção completa de PII nem filtragem abrangente de conteúdo.
- É menor e tem licença mais simples que os grandes corpora mistos. Recomendo começar com uma amostra pequena, preservando os metadados e auditando a qualidade.
- É literatura, não diálogo de assistente; precisa de um conjunto separado de instruções e ferramentas escrito/revisado para ULTRON.

### 2. nicholasKluge/Pt-Corpus
https://huggingface.co/datasets/nicholasKluge/Pt-Corpus

- Dataset card informa 5,77 milhões de linhas, 11,5 GB em Parquet e cerca de 4,1 bilhões de tokens na versão tokenizada.
- É uma mistura de fontes/licenças: Wikipedia CC BY-SA, CulturaX ODC-By/CC0, OSCAR CC0, CCc100 sob termos Common Crawl e outras fontes.
- O próprio card alerta para PII potencial, conteúdo ofensivo e trechos traduzidos com erros.
- Não usar o pacote inteiro sem selecionar fontes e licenças compatíveis. Não assumir que "open" significa domínio público ou uso irrestrito.

### 3. Carolina — Corpus de Português Brasileiro
https://corpuscarolina.ime.usp.br/en/docs

- Corpus acadêmico de português contemporâneo com licenças variadas por documento.
- O projeto informa que cada documento possui licença específica; é necessário preservar metadados e respeitar restrições individuais.
- Não usar como corpus homogêneo sem filtrar licença e metadados.

## Princípios obrigatórios da ingestão

1. Registrar dataset, versão/revisão, URL, licença, data de acesso e atribuição.
2. Manter provenance por documento; nunca misturar fontes e perder origem.
3. Fazer streaming e limitar bytes/tokens, em vez de baixar dezenas de GB para o GitHub.
4. Remover HTML/wiki markup, normalizar Unicode, filtrar texto curto, lixo, spam e conteúdo fora de português.
5. Deduplicar exata e aproximada; dividir treino/validação/teste por documento antes de tokenizar para evitar vazamento.
6. Filtrar emails, telefones e identificadores evidentes. Como filtros regex não removem nomes ou PII de forma confiável, a fonte ainda exige auditoria e um processo de remoção.
7. Manter avaliação fixa em PT-BR: fluência, compreensão, cálculo, instruções, factualidade, segurança e chamadas de ferramentas.
8. Guardar hash do corpus e config no checkpoint. Nunca publicar um peso sem licença, origem e métricas conhecidas.

## Plano de treino realista

- Etapa A: classificador de intenção próprio (já existe, 225 exemplos, 11 classes); expandir dados com exemplos balanceados e teste fora da amostra.
- Etapa B: tokenizer BPE próprio treinado apenas no corpus permitido. Medir redução de sequência em português comparado ao tokenizer byte-level.
- Etapa C: pré-treino causal do zero em corpus filtrado, com checkpoints, warmup, scheduler, clipping, validação por documento e early stopping.
- Etapa D: instruction tuning apenas com exemplos próprios/licenciados, separados do corpus de pré-treino.
- Etapa E: exportação Core ML e avaliação real no iPhone 11 Pro; medir tokens/s, latência do primeiro token, RSS, energia e aquecimento.
- Etapa F: só conectar ao chat quando vencer um benchmark mínimo e passar testes de segurança.

## Referências de escala

Hoffmann et al., *An empirical analysis of compute-optimal large language model training*, NeurIPS 2022:
https://proceedings.neurips.cc/paper_files/paper/2022/hash/c1e2faff6f588870935f114ebe04a3e5-Abstract.html

O estudo compara mais de 400 modelos e mostra que parâmetros e tokens de treino precisam crescer juntos sob orçamento de computação. A regra prática ~20 tokens/parâmetro é apenas uma aproximação para planejar; dados, arquitetura, tokenizer, objetivo e compute alteram o resultado.

## Decisão

O primeiro piloto deve usar streaming de `dataseek/ptbr-books-publicos` (CC0 1.0), em uma amostra limitada e com auditoria; não usar o corpus misto de 50 GB ou o PT-BR Wiki sem tratar suas licenças e PII. O corpus literário precisa ser complementado por exemplos próprios de instruções/diálogos, pois não ensina uso de ferramentas.

Não iniciar um treino longo com o corpus atual de 1.823 bytes. Primeiro preparar uma amostra PT-BR licenciada, filtrada, deduplicada e documentada; depois treinar e medir. Isso evita gastar horas de CPU para produzir um checkpoint que apenas memoriza 24 linhas.
