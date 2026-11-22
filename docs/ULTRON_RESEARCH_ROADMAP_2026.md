# Pesquisa técnica e plano de evolução do ULTRON — novembro de 2026

Este documento separa o que já existe, o que foi testado e o que ainda é hipótese. A meta é evoluir o ULTRON sem trocar seu núcleo por uma API de terceiros ou pesos pré-treinados.

## 1. Diagnóstico real

O núcleo atual já possui:
- classificador próprio de intenções e habilidades determinísticas;
- planejador local, execução limitada de tarefas, pesquisa web e crítico heurístico;
- memória associativa lexical esparsa, com recompensa limitada;
- API FastAPI e diagnóstico de RSS;
- aplicativo iOS com chat SSE, monitor, fala, copiar, compartilhar e Atalhos;
- Transformer decoder-only experimental, treinado de inicialização aleatória.

O que ainda não existe:
- LLM generativo de qualidade geral conectado ao chat;
- memória pessoal realmente isolada por instalação;
- embeddings semânticos próprios para busca de memória;
- KV cache para geração incremental;
- benchmark independente de diálogo, factualidade, ferramentas e retenção;
- validação física de todos os fluxos no iPhone.

A memória associativa lexical não é um modelo semântico. O crítico atual é uma checklist heurística, não um verificador factual. O chat público não deve ler nem gravar a memória privada global.

## 2. Dados e treinamento do zero

Fonte piloto: `dataseek/ptbr-books-publicos`, ficha em https://huggingface.co/datasets/dataseek/ptbr-books-publicos . A ficha declara CC0-1.0 e domínio público, mas também avisa que o material não foi sanitizado de PII, pode conter vieses e que os metadados de origem devem ser preservados. O filtro regex do ULTRON não garante anonimização.

Regras:
1. manter manifesto, licença, hashes e proveniência por documento;
2. dividir por documento/hash antes de tokenizar, nunca por janelas aleatórias sobrepostas;
3. ajustar o BPE apenas no split de treino;
4. manter validação para early stopping e teste intocado para avaliação final;
5. não publicar texto bruto ou checkpoints sem revisar risco de PII;
6. misturar literatura com dados de instrução licenciados e revisados antes de esperar comportamento de assistente.

O corpus literário ensina regularidades de língua, não obediência a instruções, diálogo, uso de ferramentas ou factualidade atual. A próxima etapa deve criar um conjunto PT-BR de instruções e tarefas com respostas verificáveis, escrito/revisado e com licença explícita.

## 3. Métricas corretas

Perplexidade é útil para acompanhar o mesmo modelo/tokenizador. Não é comparável diretamente entre tokenizadores BPE e byte-level. O pipeline agora calcula bits-per-byte (BPB), normalizado pelo tamanho UTF-8, para comparações mais justas.

BPB ainda é apenas uma métrica de predição de texto. Não prova que o modelo responde perguntas, segue instruções ou usa ferramentas. Para isso, manter um conjunto fixo e versionado de casos:
- conversa multi-turno e referência ao contexto;
- português brasileiro, acentuação, gírias e erros de digitação;
- matemática e raciocínio com resposta determinística;
- extração de fatos de texto fornecido;
- uso correto de ferramenta e recusa quando a ferramenta não existe;
- alucinação, citação e calibração de incerteza;
- privacidade, prompt injection e dados de terceiros;
- retenção de tarefas antigas depois de novas atualizações.

Registrar por versão: sucesso por tarefa, regressões, BPB, loss, p50/p95 de latência, tokens/s, pico RSS, tamanho do checkpoint, parâmetros, seed, hashes e licença. Nunca editar o conjunto dourado para fazer um candidato passar.

Referências:
- Hugging Face, treinamento de LM do zero: https://huggingface.co/blog/how-to-train
- Paloma / avaliação de perplexidade: https://papers.nips.cc/paper_files/paper/2024/file/760b2d94398aa61468aa3bc11506d9ea-Paper-Datasets_and_Benchmarks_Track.pdf
- Bits-per-byte e comparação entre tokenizadores: https://www.stanleyjacob.dev/classes/language-models-from-scratch

## 4. Arquitetura de baixo recurso

Manter três planos separados:
- API de 512 MB: FastAPI, autenticação, rate limit, ferramentas pequenas, cache limitado e armazenamento. Não instalar PyTorch nem carregar o checkpoint generativo no processo web.
- iPhone: testar conversão para Core ML, quantização e inferência local no A13; medir latência, RAM, energia e tamanho no iPhone 11 Pro real. Core ML pode despachar para CPU, GPU e Neural Engine: https://developer.apple.com/documentation/coreml
- Treinamento: GitHub Actions/runner sob demanda, separado do serviço de produção; salvar artefatos com manifesto e expiração, sem publicar automaticamente.

Uma estratégia realista é manter o modelo experimental no telefone ou como worker separado, e usar o servidor leve para orquestração. Antes de escolher tamanho, medir no dispositivo: modelo fp16/int8, contexto, KV cache e tempo até o primeiro token. Não assumir que a Neural Engine aceita qualquer grafo convertido.

Referência de implementação didática com BPE, Transformer e KV cache: https://github.com/eatoften/Decoder_Only_Transformer_from_Scratch . É referência de técnica, não de pesos.

## 5. Memória e aprendizagem contínua

A primeira evolução de memória deve ser isolamento e segurança, não embeddings:
- identidade aleatória por instalação;
- credencial individual revogável, armazenada no Keychain;
- memória e histórico com owner_id obrigatório em todas as consultas;
- migração sem atribuir registros antigos a qualquer instalação;
- exportar/apagar dados e limites de tamanho;
- evitar guardar senhas, tokens, dados financeiros ou informações sensíveis sem pedido explícito.

Depois disso, implementar recuperação híbrida: lexical/BM25 primeiro; embeddings locais quantizados só quando houver medição que justifique o custo. SQLite pode guardar vetores sem um serviço separado: https://www.sqlite.ai/sqlite-vector . Testar primeiro busca lexical porque já é leve e não depende de um modelo de embedding externo.

Aprendizagem contínua deve atualizar experiências, skills e rotinas versionadas antes de alterar pesos. Comparar agente com memória versus sem memória, reavaliar tarefas antigas e medir esquecimento. Referências:
- SWE-Bench-CL: https://arxiv.org/abs/2507.00014
- PAST-Bench: https://arxiv.org/abs/2608.04003
- Repositório de avaliação contínua: https://github.com/thomasjoshi/agents-never-forget

## 6. Autoevolução segura

Ciclo proposto:
1. observar falha com logs sem segredos;
2. reproduzir com teste;
3. criar hipótese e métrica antes de alterar;
4. trabalhar em branch isolada;
5. executar suíte fixa, benchmarks e verificação de segurança;
6. comparar candidato com baseline e reexecutar tarefas antigas;
7. abrir PR com evidências;
8. revisão humana e rollback fácil.

A automação nunca pode editar seus próprios critérios dourados, expor segredos, executar código remoto não confiável ou publicar diretamente. Mudanças de skills/prompt/configuração podem ser mais baratas e reversíveis do que retreinar pesos a cada falha.

## 7. iOS

Usar apenas APIs públicas. Prioridades: Keychain, App Intents/Atalhos, Speech, compartilhar, calendário/lembretes com consentimento e Core ML. O iOS controla quando tarefas de background rodam; não prometer agente contínuo ou controle irrestrito de outros apps.

Documentação: https://developer.apple.com/documentation/coreml e https://developer.apple.com/documentation/appintents

## 8. Sequência recomendada

P0 — Integridade do treino BPE: corrigir dependências/CLI/metadados; testar treino completo em miniatura; comparar BPB; manter o checkpoint experimental fora do chat.

P1 — Memória segura por instalação: pairing com código de uso único, credencial revogável, Keychain, isolamento no banco e testes de dois usuários.

P2 — Benchmark de diálogo e instrução PT-BR: dataset licenciado, split por documento, golden set imutável e métricas de tarefa.

P3 — Inferência: KV cache, geração incremental, limites de contexto, quantização e benchmark no iPhone 11 Pro; avaliar Core ML antes de integrar.

P4 — Agente: planner → ferramenta allowlisted → verificador; limites de passos, timeout, orçamento e confirmação humana para ações externas.

P5 — Continual learning: replay de tarefas antigas, detecção de esquecimento, versionamento de skills e promoção apenas se o baseline não regredir.

## 9. Critério para declarar uma etapa pronta

Uma melhoria só é "concluída" quando:
- código está no commit/PR identificável;
- testes relevantes passaram no HEAD atual;
- artefato e métricas são verificáveis;
- latência/RAM são medidas no ambiente declarado;
- limitações e rollback estão documentados.

Compilar IPA não é o mesmo que instalar e validar no iPhone físico. Treinar checkpoint não é o mesmo que construir um assistente geral. O ULTRON deve comunicar essa diferença com honestidade.
