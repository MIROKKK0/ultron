# ULTRON — integração do conectoma FlyWire completo

## O que a pesquisa confirmou

O projeto upstream `eonsystemspbc/fly-brain` implementa o modelo LIF de
Drosophila baseado no FlyWire FAFB v783. O snapshot FlyWire FAFB v783 lista 139.255 neurônios e aproximadamente 3,7 milhões de pares conectados; o modelo Shiu usado pelo runner cobre 138.639 (99,56%) e não inclui 616 neurônios do snapshot. O runtime agora expõe essa cobertura explicitamente; não inventa pesos ou atividade para os 616 ausentes. O runner PyTorch usa uma
matriz esparsa CSR e o passo temporal de 0,1 ms. Os dados de conectividade e
completude são arquivos separados do código.

O modelo upstream é um simulador neurocientífico de entrada sensorial e
propagação de spikes. Ele não é, por si só, um modelo de linguagem, não recebe
texto arbitrário como entrada sem um mapeamento sensorial validado e não gera
português. Portanto, não é correto afirmar que importar o conectoma transforma
automaticamente ULTRON em uma IA geral ou consciente.

## Integração adicionada

- `backend/flywire_runtime.py` carrega o runner PyTorch upstream, verifica os
  dados v783 e executa sessões persistentes de simulação em CPU. A rota
  `GET /brain/status` agora informa separadamente prontidão, arquivos e
  dependências ausentes, runtime realmente carregado e modo habilitado, sem
  expor caminhos internos do host.
- `scripts/bootstrap_flywire.sh` faz clone raso do repositório upstream, que contém os arquivos de dados usados por esse runner; os dados grandes não são versionados no Git do ULTRON.
- `requirements-flywire.txt` mantém PyTorch/Arrow isolados do servidor leve.
- `backend/perception_bridge.py` adiciona uma ponte conservadora v2: intenções positivas e inequívocas de alimentação são mapeadas para `sugar`, intenções positivas e inequívocas de locomoção para `p9`; negações e pedidos mistos são rejeitados como ambíguos, e linguagem não coberta é marcada como não mapeada.
- `POST /brain/perception` permite testar essa classificação sem salvar a mensagem. A ponte é roteamento de intenção, não percepção geral nem codificação neural treinada.
- O runtime aceita somente os estímulos documentados pelo upstream (`sugar` e `p9`). Ele não inventa uma tradução semântica para mensagens arbitrárias.
- Se dados ou dependências estiverem ausentes, a execução falha explicitamente;
  não declara o microcircuito de 48 neurônios como cérebro completo.
- Para permitir que mensagens de chat com os estímulos mapeados acionem a simulação,
  configure `ULTRON_ENABLE_FULL_FLYWIRE=1` somente depois de instalar e validar
  o conjunto completo no host. O mapeamento atual é intencionalmente limitado a intenções positivas de alimento/açúcar (sugar) e movimento/caminhada (p9).

## Preparar e testar

Em Linux com Git LFS, disco e memória suficientes:

```bash
git lfs version
bash scripts/bootstrap_flywire.sh
python -m pip install -r requirements-flywire.txt
ULTRON_FLYWIRE_ROOT=vendor/fly-brain python -m unittest tests.test_flywire_runtime -v
```

O carregamento da matriz CSR pode consumir centenas de MB adicionais. A simulação
CPU de 138k neurônios e milhões de arestas é muito mais pesada que a API atual.
Não habilite esse caminho em Render Free: o plano leve não oferece a memória/CPU
necessária para garantir uma execução estável. O servidor só deve ativá-lo após
um benchmark real no hardware de destino.

## Estado atual e limites ainda não resolvidos

O cérebro completo não está ativo no Render Free. A validação de CI comprova
que a simulação de teste consegue carregar o conectoma e executar passos no
runner do GitHub, mas não prova que o processo de produção tem memória, CPU,
dados LFS ou tempo de execução suficientes. A API mantém o microcircuito leve
como núcleo operacional e só declara FlyWire completo quando o runtime real
está carregado na memória.

1. A ponte atual cobre somente duas classes explícitas e rejeita intenções negadas/mistas. O aprendizado associativo valida entradas finitas, índices e limites de atividade, mantém pesos limitados e persiste checkpoints no banco. Para ampliar a linguagem natural, é necessário treinar e validar um mapeador para populações sensoriais usando IDs, anotações, regiões e protocolos experimentais corretos; não basta adicionar sinônimos.
2. Os experimentos upstream `sugar` e `p9` são estímulos de laboratório, não
   um vocabulário geral.
3. A simulação não produz texto; uma camada linguística local independente
   ainda precisa ser executada no dispositivo/servidor, sem API paga.
4. Plasticidade, aprendizagem e alterações de pesos não podem ser anunciadas
   como autoaprendizagem geral. Qualquer aprendizado futuro deve ser mensurável,
   persistente, reversível e testado.
5. A licença do código upstream é GPL-2.0-or-later; os dados derivados do
   FlyWire têm avisos/termos próprios. Preserve os avisos e valide a licença
   aplicável ao redistribuir dados.

## Fontes primárias

- https://github.com/eonsystemspbc/fly-brain
- https://github.com/eonsystemspbc/fly-brain/blob/main/code/run_pytorch.py
- Shiu et al., modelo LIF baseado no conectoma adulto de Drosophila.
- Dorkenwald et al. (2024), FlyWire whole-brain connectome, Nature.


## Investigação da lacuna de 616 neurônios — 2026-11-15

A pesquisa encontrou uma implementação pública independente, dawsonamf/siliconfly, que declara avançar os 139.255 neurônios e 15.091.983 arestas do FAFB v783 em um simulador LIF Metal. Ela usa um pacote binário próprio (neurons.bin e synapses.bin) e pesos assinados derivados de tabelas Codex/Princeton e regras de modelagem documentadas. O autor informa teste em macOS com Apple Silicon M4 Pro; isso não demonstra compatibilidade nem desempenho no iPhone 11 Pro.

Também foi encontrada a implementação kornel77777/fly-brain-sim, que mantém separadas as tabelas shiu_connections e connections do Codex. Ela alerta que os pesos/tabelas de sinapses são de fontes diferentes e não podem ser misturados. A análise independente descreve os 616 excluídos do modelo Shiu como predominantemente aferentes sensoriais, mas a razão exata da exclusão ainda não foi confirmada.

Fontes consultadas:
- https://github.com/dawsonamf/siliconfly
- https://github.com/kornel77777/fly-brain-sim
- https://github.com/eonsystemspbc/fly-brain

### Decisão técnica segura

Não copiar os 616 IDs para dentro da matriz Shiu nem completar pesos por zero, média, aleatoriedade ou interpolação. Isso produziria uma rede numericamente maior, mas não o conectoma validado. O caminho correto é um segundo backend experimental, isolado do runner Shiu, que consuma o pacote completo v783 e preserve a proveniência/licença CC BY-NC 4.0 dos dados FlyWire. Antes de ativá-lo no ULTRON, exigir:

1. Manifesto e SHA-256 verificados para cada binário e versão do dataset.
2. Correspondência exata de 139.255 IDs únicos, incluindo os 616 ausentes no modelo Shiu, sem IDs duplicados ou truncados.
3. Auditoria das 15.091.983 arestas, índices CSR, pesos com sinal e contagens contra os arquivos-fonte publicados.
4. Testes CPU de referência reproduzíveis e comparação bit a bit/por tolerância com o kernel Metal.
5. Testes de estímulos e circuitos anotados; documentar explicitamente as escolhas de LIF, ruído, delays, normalização e sinapses sem neurotransmissor.
6. Benchmark real no iPhone 11 Pro (RAM, temperatura, bateria e tempo por passo).
7. Manter o modelo Shiu atual como trilha científica separada; não fundir pesos incompatíveis nem chamar as duas parametrizações de uma só simulação.

Até esses gates passarem, o status correto continua sendo 138.639/139.255 neurônios no modelo Shiu (99,56%) e 616 fora dele. A implementação Metal citada é uma rota de pesquisa promissora, não uma integração já validada no ULTRON.
