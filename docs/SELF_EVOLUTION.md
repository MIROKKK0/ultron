# ULTRON — skills e autoevolução segura

## Núcleo leve atual

- Classificador de intenções próprio, treinado do zero com 225 exemplos em português.
- Tokenizador próprio de bytes UTF-8, palavras e n-gramas, com 4096 IDs hash.
- Multinomial Naive Bayes com pesos próprios versionados em `backend/model/intent_model.json`.
- Inferência na CPU usando apenas a biblioteca padrão do Python; sem downloads de modelos, GPU ou provedores externos.
- Skills nativas: conversa, ajuda, autoconhecimento, planejamento, cálculo/pesquisa via ferramentas existentes, status, memória protegida, autoavaliação e autoevolução segura.

## Limite explícito

O modelo é um classificador de intenções, não um LLM generativo. Ele aprende a encaminhar pedidos conhecidos para habilidades locais; perguntas abertas continuam limitadas pelo decodificador determinístico. Não deve ser anunciado como equivalente ao ChatGPT ou como inteligência geral.

## Ciclo de evolução

1. Medir a qualidade em conjunto de validação fixo.
2. Revisar exemplos novos antes de adicioná-los ao corpus.
3. Treinar pesos novamente com `python scripts/train_intent_model.py`.
4. Verificar reprodutibilidade com `python scripts/train_intent_model.py --check`.
5. Executar toda a suíte de testes e medir latência/RAM.
6. Abrir PR com corpus, pesos, métricas e regressões.
7. Exigir revisão humana antes de integrar ou implantar.

Feedback público, páginas da web e mensagens de usuários não são incorporados automaticamente ao corpus. Isso evita envenenamento de dados, prompt injection e gravação de informações pessoais. Skills são funções Python internas; arquivos externos de skills são documentação e nunca são executados como código.
