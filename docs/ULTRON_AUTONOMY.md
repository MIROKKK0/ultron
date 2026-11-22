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

O núcleo persiste memórias e relações em SQLite e classifica a recuperação lexical por relevância. Isso melhora a busca por palavras e contexto textual, mas ainda não equivale a embeddings semânticos.

A API `ultron_api.py` oferece rotas autenticadas para consultar o grafo, sincronizar snapshots isolados por ID de instalação e enfileirar tarefas. O iOS guarda o token e o ID de instalação no Keychain, envia o histórico local ao endpoint de sincronização e carrega o grafo remoto. Se a API/token estiver indisponível, o visualizador usa o histórico local e informa essa origem.

O visualizador SceneKit/SwiftUI permite rotação, zoom e seleção de nós. Ainda falta validar o Swift no projeto Xcode/IPA, implantar a API com `ULTRON_API_TOKEN` e armazenamento persistente, testar a sincronização real no iPhone e adicionar embeddings ou um modelo semântico leve. O worker também precisa ser implantado em processo contínuo com volume persistente; o código sozinho não o mantém online.
