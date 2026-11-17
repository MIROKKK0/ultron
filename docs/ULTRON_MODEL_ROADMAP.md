# ULTRON — pesquisa técnica, estado real e roadmap do cérebro próprio

Atualizado em 17/11/2026. Este documento separa capacidades implementadas, experimentos e metas futuras. Nenhuma métrica de loss, sozinha, prova inteligência geral.

## Estado atual verificado

### Assistente e backend
- O chat de produção usa um classificador próprio de intenções (Naive Bayes, n-gramas, 4.096 buckets, 225 exemplos anotados) e habilidades determinísticas.
- O endpoint de streaming `/chat/stream` respondeu com os eventos `processing`, `responding` e `final` no smoke test ao vivo.
- O teste de runtime mediu RSS de aproximadamente 73,97 MB dentro de um orçamento declarado de 512 MB (13,8% naquele instante). É uma medição pontual, não um pico de carga.
- O Transformer não está conectado ao chat de produção. O backend não deve carregar checkpoints experimentais sem passar pelas etapas de avaliação e memória.

### Modelo generativo próprio
- Arquitetura decoder-only pequena, 2 blocos, largura 64 e contexto configurável.
- Inicialização aleatória; nenhum peso de outro modelo é usado.
- Tokenizador byte-level continua como fallback.
- Foi implementado tokenizador BPE próprio, treinado apenas no split de treino, com vocabulário configurado em 2.048 tokens.
- Treino: AdamW, clipping, warmup, decaimento cosseno, amostragem vetorizada, seleção do melhor checkpoint por validação, early stopping e avaliação de teste separada.
- Checkpoints guardam configuração, hashes do corpus/tokenizador, passos executados e métricas.

### Baseline já treinado
Primeira rodada de demonstração:
- 39 documentos; aproximadamente 496 mil caracteres preparados.
- 2.000 passos, cerca de 124 mil parâmetros, tokenizer byte-level.
- Perplexidade de validação reportada: aproximadamente 12,64; perda no teste: aproximadamente 2,48.
- O resultado prova que o pipeline treina e avalia; não prova capacidade de conversa, conhecimento geral ou equivalência ao ChatGPT.

### Rodada ampliada
A execução `ULTRON PT-BR from-scratch pretraining` usa até 5 milhões de caracteres, tokenizador BPE próprio, até 10.000 passos e early stopping. O checkpoint e as métricas devem ser avaliados após a conclusão do workflow; não chamar o modelo de pronto antes disso.

## Dados e licenças

Fonte escolhida para o primeiro pré-treino: [dataseek/ptbr-books-publicos](https://huggingface.co/datasets/dataseek/ptbr-books-publicos), corpus de livros em domínio público com licença declarada CC0-1.0. A página do dataset informa cerca de 28,2 mil documentos e 355,9 milhões de caracteres. O ULTRON baixa apenas uma amostra limitada em streaming, preserva manifesto/proveniência e não coloca o corpus bruto no Git.

Filtros atuais incluem normalização Unicode, remoção de URLs/caracteres de controle, deduplicação, rejeição de documentos suspeitos e máscaras para alguns identificadores diretos. Regex não remove todos os dados pessoais; o manifesto registra essa limitação. Não distribuir artefatos sem conferir a licença e a proveniência de cada fonte.

Não usar datasets compostos por licenças incompatíveis ou saídas de modelos externos sem revisão explícita. Não usar pesos pré-treinados.

## Pesquisa técnica e o que ela significa para ULTRON

1. **Escala de dados e parâmetros — Chinchilla (NeurIPS 2022).** O estudo avaliou mais de 400 modelos de 70 milhões a mais de 16 bilhões de parâmetros, treinados com 5 a 500 bilhões de tokens, e mostrou que tamanho do modelo e quantidade de tokens precisam crescer juntos sob um orçamento de computação. A conhecida regra aproximada de 20 tokens/parâmetro não deve ser extrapolada como garantia para nosso modelo minúsculo, fora da faixa experimental do artigo.  
   https://proceedings.neurips.cc/paper_files/paper/2022/hash/c1e2faff6f588870935f114ebe04a3e5-Abstract.html
2. **Treino GPT do zero — Andrej Karpathy.** A aula e o repositório `build-nanogpt` mostram tokenizer, batches, atenção, validação e otimização; o material deixa claro que pré-treino base não equivale a um chatbot e que o GPT-2 de 124M exige muito mais computação.  
   https://www.youtube.com/watch?v=l8pRSuU81PU  
   https://github.com/karpathy/build-nanogpt
3. **Atenção eficiente — PyTorch SDPA.** O núcleo usa `scaled_dot_product_attention`; kernels e ganhos dependem do dispositivo e do formato. Medir CPU real do Render em vez de presumir aceleração.  
   https://docs.pytorch.org/tutorials/intermediate/scaled_dot_product_attention_tutorial
4. **iPhone — Core ML.** A Apple permite executar modelos próprios em CPU, GPU e Neural Engine; Core ML Tools oferece quantização e paletização. A conversão só deve acontecer depois de congelar arquitetura e validar equivalência numérica/qualidade.  
   https://developer.apple.com/documentation/coreml  
   https://github.com/apple/coremltools/blob/main/docs-guides/source/opt-overview.md
5. **Limites de modelos pequenos.** TinyStories e outros experimentos demonstram que modelos pequenos podem aprender padrões coerentes em domínios estreitos, mas também que um modelo base sem instruction tuning não é um assistente factual.  
   https://arxiv.org/abs/2305.07759

## Arquitetura cognitiva pretendida

A analogia útil com um cérebro é funcional, não biológica. O sistema deve separar:
- **Percepção/entrada:** texto, voz e ações explícitas do usuário.
- **Memória de trabalho:** contexto recente limitado por requisição.
- **Memória episódica:** histórico local no iPhone, com controle para apagar.
- **Memória semântica:** busca em documentos e fontes com proveniência.
- **Planejador executivo:** decompor objetivo em etapas e escolher skills.
- **Ferramentas:** cálculo, pesquisa, calendário/Shortcuts e ações iOS autorizadas.
- **Crítico/verificador:** checar fatos, resultados, permissões e testes.
- **Aprendizado:** feedback e avaliação alteram prioridades e propostas; pesos só mudam por treinamento versionado e testado.

O módulo associativo atual usa codificação lexical esparsa com hash, não embeddings semânticos nem uma simulação biológica. Não descrevê-lo como cérebro humano.

## Próximas etapas por prioridade

### P0 — fechar o ciclo atual
- Concluir a rodada BPE de 5M caracteres/10k passos.
- Guardar checkpoint, tokenizer, hashes, manifesto e logs.
- Gerar amostras fixas e comparar validação/teste com o baseline byte-level.
- Rejeitar checkpoint que só memorize ou produza texto repetitivo.

### P1 — tornar o modelo assistente
- Criar dados de instrução originais e auditáveis, separados do pré-treino.
- Implementar SFT com máscara de loss apenas na resposta do assistente.
- Criar benchmark PT-BR de instruções, contexto, matemática, factualidade, tool calling e segurança.
- Fazer avaliação humana de respostas; não selecionar apenas por perplexidade.

### P2 — inferência e integração
- Implementar carregamento opcional do checkpoint com limite rígido de memória e timeout.
- Medir latência do primeiro token, tokens/s, RSS e concorrência no serviço de 512 MB.
- Manter fallback determinístico se o modelo estiver ausente, lento ou abaixo do limite.
- Só então criar versão de produção e endpoint experimental separado.

### P3 — iPhone
- Fechar build do simulador e IPA; testar instalação/atualização no dispositivo real.
- Manter ações nativas com App Intents/Shortcuts e permissões explícitas.
- Depois de congelar o modelo, avaliar exportação Core ML e quantização no iPhone 11 Pro.

### P4 — autoevolução segura
- Observar falhas → reproduzir → abrir teste → propor patch em branch → rodar CI/benchmarks → revisão humana.
- Não permitir auto-merge, publicação de IPA, troca de pesos de produção ou ações privadas sem autorização.
- Cada release precisa de rollback, hashes, licença, métricas e evidência de build.

## Critério de honestidade

O objetivo atual é um assistente híbrido, leve e verificável, com um modelo generativo próprio em evolução. Com CPU gratuita, corpus amostrado e orçamento de 512 MB, não é realista prometer qualidade igual ou superior ao ChatGPT. A qualidade precisa ser demonstrada em benchmarks e uso real; até lá, o Transformer continua experimental e o chat de produção continua usando as habilidades locais.
