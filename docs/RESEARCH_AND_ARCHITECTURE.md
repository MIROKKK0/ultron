# Pesquisa técnica e arquitetura recomendada para o ULTRON

Atualizado em 17/11/2026. Este documento separa resultados verificados, protótipos e objetivos ainda não atingidos.

## Diagnóstico do repositório
O núcleo ativo usa classificador de intenções próprio, roteador de skills e fallback determinístico. Isso é leve e rápido, mas não é um modelo generativo geral. O Transformer em `training/generative/` é um experimento inicial de 118 mil parâmetros, com pesos aleatórios e corpus autoral de smoke test. Ele não deve ser ligado ao chat nem anunciado como assistente geral.

O backend web deve continuar sem PyTorch e sem carregar pesos generativos no processo de 512 MB. O app iOS pode funcionar como interface e executor de ações autorizadas; iOS não permite controle irrestrito de outros aplicativos.

## Arquitetura-alvo em camadas
1. **Gateway leve:** FastAPI, limites de tamanho/concorrência, autenticação por instalação para memória privada, timeout e fallback.
2. **Roteador rápido:** classificador próprio e skills determinísticas para tarefas conhecidas.
3. **Memória:** separar perfil, episódios e documentos; começar por busca lexical, depois medir se embeddings melhoram hit@k. Guardar origem, data, confiança, retenção e exclusão.
4. **Planejador/executor:** ferramentas tipadas, allowlist, limites de passos, timeout, cancelamento e aprovação humana para ações sensíveis.
5. **Crítico/verificador:** validar resultado de ferramenta, formato e afirmações de execução. Sem modelo generativo, a crítica continua heurística.
6. **Aprendizagem:** registrar erros/feedback com consentimento, gerar casos de avaliação, propor mudanças em branch, testar e manter rollback. Não treinar indiscriminadamente com conversas públicas.
7. **Modelo próprio:** dados próprios/licenciados, tokenizer versionado, Transformer causal, treino, validação separada, checkpoint, avaliação e exportação.
8. **iOS:** App Intents/Atalhos, Speech, compartilhamento e APIs nativas com permissão/confirmacão.

## Otimizações imediatas
- Usar `scaled_dot_product_attention(..., is_causal=True)` para evitar criar máscara causal LxL em cada forward e permitir kernels otimizados.
- Separar treino e validação antes de extrair janelas, evitando vazamento por sobreposição.
- Medir loss/perplexidade em validação; loss de treino sozinha não comprova generalização.
- Salvar checkpoint por arquivo temporário e renomeação atômica.
- Preservar modo train/eval após geração.
- Manter PyTorch/treino fora do servidor 512 MB.
- Medir p50/p95, RSS, tamanho do artefato e taxa de sucesso por caso.

## Projetos e vídeos de referência
- [karpathy/build-nanogpt](https://github.com/karpathy/build-nanogpt): construção incremental de GPT e aula em vídeo.
- [jlinoff/tiny-llm-in-rust](https://github.com/jlinoff/tiny-llm-in-rust): BPE, Transformer pequeno, autograd, treino e KV cache didáticos.
- [MarcoKl99/LLM-Lab](https://github.com/MarcoKl99/LLM-Lab): pipeline reproduzível e métricas de validação.
- [RamiJaloudi/small-llm-from-scratch](https://github.com/RamiJaloudi/small-llm-from-scratch): dados, tokenizer, treino, checkpoints e presets de GPU.
- [freeCodeCamp — Train Your Own LLM](https://www.youtube.com/watch?v=9Ge0sMm65jo): corpus, BPE, Transformer, pré-treino e instruction tuning.
- [Tiny GPT from scratch (2026)](https://www.youtube.com/watch?v=NiZdkwx9t5Q): tokenização, atenção causal, loss, treino e avaliação.
- [EvoSkill](https://github.com/sentient-agi/EvoSkill): aprende skills reutilizáveis de falhas e seleciona variantes por avaliação; depende de modelo propositor.
- [Awesome Self-Improving Agents](https://github.com/interactivetech/awesome-self-improving-agent): mapa de pesquisa sobre evolução de memória, skills, harnesses e políticas.
- [skillmem](https://github.com/liza-studio/skillmem): memória local com proveniência e confiança explícitas.
- [EvoAgent](https://github.com/mingbo-yang/EvoAgent): referência para ReAct, ferramentas, memória, observabilidade e avaliação; usa provedores de modelo, portanto não é dependência do ULTRON.

## Integração iPhone — documentação oficial
- [App Intents](https://developer.apple.com/documentation/appintents): ações expostas a Siri, Spotlight e Atalhos.
- [Core ML](https://developer.apple.com/documentation/coreml): inferência no CPU/GPU/Neural Engine e adaptação on-device.
- [Background Tasks](https://developer.apple.com/documentation/backgroundtasks/): execução em background é oportunista e pode ser suspensa.
- [Otimização de CPU](https://developer.apple.com/documentation/xcode/scheduling-cpu-work-efficiently): cache, evitar alocação repetida, usar eventos e frameworks nativos.

## Plano com gates
**A — confiabilidade:** baseline de testes, p50/p95, RSS, teste de causalidade, checkpoint íntegro, API/streaming e IPA CI.

**B — cérebro operacional:** memória isolada por instalação, ferramentas com schema/allowlist, aprovação, cancelamento e logs; avaliar hit@k.

**C — modelo próprio:** corpus amplo próprio/licenciado e deduplicado; validação fixa em português; avaliação humana de utilidade, factualidade, segurança e instruções; medir perplexidade, latência, RAM e erros; quantizar e avaliar Core ML ou runtime separado.

**D — autoevolução:** transformar erros em testes; testar uma hipótese por vez; rodar regressão, segurança, latência e RAM; manter variantes e trilha de auditoria; aprovação antes de merge/deploy e rollback.

## Limites
Um modelo com ~118 mil parâmetros e corpus de poucos KB demonstra o pipeline, não conversa inteligente. Treinar modelo geral do zero exige muito mais dados e computação. 512 MB é orçamento para gateway leve, não treino moderno ou modelo grande. O ganho imediato real vem de classificador rápido, memória isolada, ferramentas confiáveis, avaliação e boa experiência iOS.
