# Skills do Ultron

O Ultron suporta skills como arquivos `SKILL.md` de instruções. O carregador localiza skills incluídas no repositório e skills adicionadas em `~/.ultron/skills/`.

## Ferramentas

- `skills` — lista as skills disponíveis.
- `find_skills` — pesquisa o ecossistema usando `npx skills find` (requer Node.js/npx).
- `load_skill` — carrega as instruções de uma skill para a conversa atual.

Skills são conteúdo de instrução, não plugins executáveis. O carregador não executa scripts de terceiros. Revise origem, conteúdo, scripts e dependências antes de instalar. Instalação externa exige decisão explícita do usuário.

## Skills incluídas

- **find-skills** — descobrir e avaliar novas skills.
- **improve-codebase-architecture** — auditar arquitetura e propor melhorias seguras.

Para adicionar uma skill local, coloque seu `SKILL.md` em `~/.ultron/skills/<nome>/SKILL.md` e reinicie o Ultron.
