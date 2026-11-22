# Execução contínua e autoevolução do ULTRON

## Worker de agentes em segundo plano

`scripts/ultron_worker.py` consome a fila persistida em `UltronCore`, seleciona o especialista registrado para cada tarefa e executa o objetivo usando um modelo compatível com a API OpenAI.

Variáveis:
- `ULTRON_LLM_API_KEY` (ou `OPENAI_API_KEY`)
- `ULTRON_LLM_BASE_URL` (opcional)
- `ULTRON_LLM_MODEL` (opcional)
- `ULTRON_CORE_DB` ou `ULTRON_DATA_DIR` para localizar o SQLite

Execução contínua: `python scripts/ultron_worker.py`.
Execução de uma tarefa: `python scripts/ultron_worker.py --once`.

**Persistência:** o processo precisa rodar em um host de longa duração com armazenamento persistente montado no caminho do banco. Um runner efêmero do GitHub Actions não deve ser tratado como memória durável nem como daemon permanente. O worker foi implementado, mas ainda não está implantado em uma instância de produção.

## Autoalteração e PRs

`scripts/recursive_evolution.py` pesquisa referências públicas, inspeciona o repositório, gera um patch limitado aos diretórios permitidos e aplica o patch em uma branch de trabalho. O workflow executa:
1. testes unitários completos;
2. avaliador congelado na versão base e no candidato;
3. comparação objetiva dos scores;
4. revisão crítica separada;
5. criação de uma PR somente se os gates forem aprovados.

O avaliador congelado e o próprio gerador ficam protegidos contra alteração pelo patch. O workflow não faz merge nem deploy automaticamente: candidatos elegíveis ficam como PR para revisão humana.

## Memória e Universo Neural

O núcleo persiste memórias e relações em SQLite e agora classifica a recuperação lexical por relevância. Isso é uma base de recuperação, não embeddings semânticos. O visualizador SceneKit/SwiftUI mostra as mensagens locais do chat como nós 3D, com rotação, zoom e seleção.

Ainda faltam embeddings reais ou um modelo local leve, rotas autenticadas de sincronização, recuperação do grafo remoto no iOS e integração do arquivo Swift ao projeto Xcode/IPA. Não declare sincronização entre dispositivos ou dados semânticos completos até essas partes serem implantadas e testadas.
