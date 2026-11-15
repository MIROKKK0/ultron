# ULTRON — critérios para a versão definitiva

Este documento é o contrato de qualidade do projeto. "Definitivo" significa uma versão estável, testada e reproduzível — não uma alegação de AGI, consciência ou autoevolução irrestrita.

## Invariantes que não podem ser removidos

1. **FlyBrain é o núcleo obrigatório.** Toda solicitação deve passar pelo núcleo neural antes da seleção de estratégia/ferramenta. Qwen é somente um renderizador auxiliar de linguagem e não substitui o FlyBrain.
2. **Não fabricar neurociência.** O microcircuito LIF de 48 neurônios é um circuito compacto experimental. O modelo FlyWire FAFB v783 integrado pelo Shiu cobre 138.639 neurônios da referência de 139.255; os 616 restantes não podem receber pesos inventados nem ser descritos como simulados.
3. **Sem autoalteração em produção.** O sistema pode propor mudanças, abrir branches e executar testes. Promoção de código, mudanças de segurança e deploy exigem revisão/aprovação humana e rollback.
4. **Sem memória cruzada.** Nenhuma memória ou conversa privada pode ser compartilhada entre instalações. Não ativar memória persistente no chat público até haver identidade de instalação validada no servidor e testes de isolamento.
5. **Sem segredos no IPA.** Tokens de servidor ou chaves de provedores não podem ser embutidos no aplicativo.
6. **Relatar evidências.** Build de CI não equivale a teste em iPhone. Simulação de CI não prova que o conectoma completo está ativo no Render ou no aparelho.

## Estado confirmado na auditoria de 2026-11-15

- FlyBrain LIF compacto, memória associativa limitada e ponte de percepção estão no código.
- Há integração de pesquisa web sem chave usando DDGS; resultados são links e trechos, não conhecimento interno do conectoma.
- O ciclo planner/solver/critic usa funções locais determinísticas/heurísticas. Não são três LLMs independentes.
- Qwen3-0.6B Q4_K_M é opcional, baixado depois da instalação (~462 MiB); não está embutido no IPA.
- PR #12 melhora timeout de rede, filtragem de `<think>` e limite de geração. Ainda requer compilação e teste no iPhone 11 Pro.
- O Render Free não é ambiente aprovado para o conectoma completo; o runtime integral exige memória e CPU acima do orçamento típico do plano gratuito.
- A rota pública do chat não deve recuperar memórias privadas até o isolamento por instalação ser concluído.

## Bloqueadores para declarar a versão definitiva

### A. Segurança e privacidade — bloqueador de lançamento
- Implementar identidade de instalação verificável, preferencialmente Apple App Attest com desafio de uso único, validação no backend e assertions assinadas.
- Isolar conversas, memórias e feedback por instalação/usuário no banco.
- Aplicar rate limits compartilhados entre instâncias, quotas e proteção contra replay.
- Testar que uma instalação não consegue ler, alterar ou apagar dados de outra.
- Não aceitar um UUID enviado pelo cliente como autenticação suficiente.

### B. Cérebro e avaliação científica
- Manter o FlyBrain como etapa obrigatória e expor telemetria verdadeira.
- Criar um conjunto de tarefas reproduzível para percepção, associação, retenção, esquecimento e generalização.
- Comparar baseline sem aprendizagem com aprendizagem ativada; registrar seed, dataset, parâmetros e métricas.
- Validar qualquer novo grafo de conectoma em backend experimental separado, com checksum, IDs, CSR/edges, auditoria de sinais e comparação CPU/Metal.
- Não habilitar o conectoma completo no Render Free nem no iPhone sem medições reais de RAM, latência, bateria e temperatura.

### C. Linguagem e memória
- Medir qualidade, latência, RAM e temperatura do Qwen no iPhone 11 Pro.
- Manter resposta verificada do backend como fallback caso o modelo local falhe.
- Criar testes para streaming parcial, cancelamento, resposta vazia, tags internas, perda de rede e servidor adormecido.
- Implementar memória episódica/semântica somente depois do bloqueador A; adicionar busca, expiração, exportação e exclusão por instalação.
- Separar fatos do backend, resultados da web, memórias e texto gerado pelo modelo.

### D. Ferramentas e pesquisa
- Validar URL, timeout, tamanho de resposta e tipo de conteúdo antes de processar páginas.
- Guardar URL, título, data de coleta e trecho para cada fonte; não apresentar trecho como leitura integral.
- Exigir aprovação para ações externas irreversíveis; manter allowlist e logs sem segredos.
- Adicionar testes de indisponibilidade, respostas malformadas, prompt injection em páginas e limites de uso.

### E. Autoaperfeiçoamento seguro
- Registrar erro observado, hipótese, métrica de sucesso e baseline antes de cada experimento.
- Criar branch isolada, rodar testes e benchmarks fixos, anexar resultados e abrir PR.
- Bloquear merge/deploy automático; exigir revisão humana e rollback documentado.
- Só promover se não houver regressões de segurança, privacidade, desempenho ou comportamento.

### F. Aplicativo e distribuição
- Compilar Simulator e dispositivo em CI.
- Instalar a IPA no iPhone 11 Pro via SideStore e testar conversa, rede, modelo local, memória, reinício, background/foreground e recuperação de falhas.
- Testar instalação limpa, atualização sobre versão anterior e remoção do modelo local.
- Medir cold start, primeira resposta com servidor acordado/dormindo, tokens/s, RAM, uso de bateria e temperatura.
- Gerar checksum SHA-256 e notas de versão para cada artefato publicado.

## Portões de lançamento

| Portão | Critério para passar |
|---|---|
| G0 — Integridade | CI Python e build iOS passam; dependências fixadas |
| G1 — Segurança | App Attest/identidade, isolamento de dados, quotas e testes de privacidade |
| G2 — Cérebro | Testes de percepção/aprendizado reproduzíveis e telemetria honesta |
| G3 — Linguagem | Streaming e fallback testados; benchmark real no iPhone 11 Pro |
| G4 — Ferramentas | Pesquisa com fontes e validação; ações com autorização |
| G5 — Estabilidade | Testes de regressão, atualização, recuperação e soak test |
| G6 — Release | IPA, checksum, changelog, rollback e instalação validada no aparelho |

A versão só pode ser chamada de estável depois de passar por todos os portões. Itens não executáveis sem hardware/credenciais (App Attest e teste físico) permanecem explicitamente pendentes, nunca marcados como concluídos por inferência.
