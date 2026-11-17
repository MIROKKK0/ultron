# Skills de desenvolvimento do ULTRON

Este catálogo fornece instruções especializadas aos agentes que trabalham no repositório. Ele não altera o runtime do aplicativo, não adiciona um LLM e não modifica o FlyBrain.

## Skills incluídas

- **find-skills** — descobre e avalia habilidades externas; não instala nem executa código automaticamente.
- **improve-codebase-architecture** — audita a arquitetura e propõe melhorias testáveis, preservando o núcleo.

## Descobrir outras skills

Use o Skills CLI:

```bash
npx skills find <termos>
```

Para instalar uma skill compatível neste repositório, revise primeiro seu `SKILL.md`, scripts, dependências, licença e permissões. Depois, com autorização explícita:

```bash
npx skills add <owner/repo@skill> --agent codex
```

Confirme o caminho de instalação apresentado pelo CLI e faça revisão do diff antes de aceitar. Nunca instale em massa nem execute scripts de terceiros sem inspeção.
