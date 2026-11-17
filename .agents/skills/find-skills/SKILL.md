---
name: find-skills
description: Descobre skills externas para tarefas especializadas, avalia origem, compatibilidade, licença e segurança antes de recomendar instalação.
---

# Find Skills

Use quando uma tarefa do ULTRON exigir uma capacidade de engenharia ainda não coberta pelo fluxo atual, ou quando o usuário pedir para ampliar as capacidades dos agentes de desenvolvimento.

## Processo

1. Identifique domínio, tarefa e ambiente do agente.
2. Consulte o leaderboard do Skills Directory e pesquise com `npx skills find <termos>`.
3. Prefira fontes oficiais e mantenedores reconhecidos. Popularidade e estrelas não provam segurança.
4. Abra o repositório original e leia o `SKILL.md` completo.
5. Inspecione scripts, dependências, comandos shell, rede, acesso a arquivos, licença e compatibilidade.
6. Explique exatamente o que a skill acrescenta e o que ela não acrescenta.
7. Só instale depois de autorização explícita. Instalação não significa que a skill esteja disponível no runtime iOS/servidor.
8. Nunca execute scripts de terceiros apenas porque uma busca os encontrou.

## Restrições específicas do ULTRON

- Nenhuma skill pode substituir ou ignorar o FlyBrain.
- Nenhuma skill pode autorizar deploy, merge, release ou alteração de segredos.
- Não adicionar SDK de IA hospedada nem custos sem autorização.
- Mudanças de código devem ocorrer em branch isolada, com testes e PR revisável.
