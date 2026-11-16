# ULTRON — integração do conectoma FlyWire completo

## O que a pesquisa confirmou

O projeto upstream `eonsystemspbc/fly-brain` implementa o modelo LIF de
Drosophila baseado no FlyWire FAFB v783. O modelo tem aproximadamente 138.639
neurônios modelados e milhões de conexões dirigidas. O runner PyTorch usa uma
matriz esparsa CSR e o passo temporal de 0,1 ms. Os dados de conectividade e
completude são arquivos separados do código.

O modelo upstream é um simulador neurocientífico de entrada sensorial e
propagação de spikes. Ele não é, por si só, um modelo de linguagem, não recebe
texto arbitrário como entrada sem um mapeamento sensorial validado e não gera
português. Portanto, não é correto afirmar que importar o conectoma transforma
automaticamente ULTRON em uma IA geral ou consciente.

## Integração adicionada

- `backend/flywire_runtime.py` carrega o runner PyTorch upstream, verifica os
  dados v783 e executa sessões persistentes de simulação em CPU.
- `scripts/bootstrap_flywire.sh` busca uma revisão upstream fixada
  (`a3db62f9436074e485c0278290c2164ed6150808` por padrão; configurável por
  `ULTRON_FLYWIRE_REVISION`). Os arquivos v783 são blobs Git comuns, não Git LFS:
  completude ~3,47 MB e conectividade ~100,8 MB. O script verifica a revisão e
  exige também o arquivo LICENSE.
- `requirements-flywire.txt` mantém PyTorch/Arrow isolados do servidor leve.
- O runtime aceita somente os estímulos documentados pelo upstream (`sugar`
  e `p9`). Ele não inventa uma tradução semântica para mensagens arbitrárias.
- Se dados ou dependências estiverem ausentes, a execução falha explicitamente;
  não declara o microcircuito de 48 neurônios como cérebro completo.
- Para permitir que mensagens de chat com os estímulos mapeados acionem a simulação,
  configure `ULTRON_ENABLE_FULL_FLYWIRE=1` somente depois de instalar e validar
  o conjunto completo no host. O mapeamento atual é intencionalmente limitado a
  termos de alimento/açúcar (sugar) e movimento/caminhada (p9).

## Preparar e testar

Em Linux com Git, disco e memória suficientes:

```bash
git --version
bash scripts/bootstrap_flywire.sh
python -m pip install -r requirements-flywire.txt
ULTRON_FLYWIRE_ROOT=vendor/fly-brain python -m unittest discover -s tests -p 'test_flywire_runtime.py' -v
python scripts/validate_flywire.py
```

O artefato de validação registra o commit upstream exato e SHA-256 de cada
arquivo de dados, permitindo reproduzir e auditar o dataset usado. Para atualizar
a revisão, defina `ULTRON_FLYWIRE_REVISION` explicitamente e revise os novos
avisos/licenças antes de executar o benchmark.

O carregamento da matriz CSR pode consumir centenas de MB adicionais. A simulação
CPU de 138k neurônios e milhões de arestas é muito mais pesada que a API atual.
Não habilite esse caminho em Render Free: o plano leve não oferece a memória/CPU
necessária para garantir uma execução estável. O servidor só deve ativá-lo após
um benchmark real no hardware de destino.

## Limites ainda não resolvidos

1. O mapeamento de linguagem natural para populações sensoriais precisa de uma
   camada de percepção treinada e validada com os IDs/annotations corretos.
2. Os experimentos upstream `sugar` e `p9` são estímulos de laboratório, não
   um vocabulário geral.
3. A simulação não produz texto; uma camada linguística local independente
   ainda precisa ser executada no dispositivo/servidor, sem API paga.
4. Plasticidade, aprendizagem e alterações de pesos não podem ser anunciadas
   como autoaprendizagem geral. Qualquer aprendizado futuro deve ser mensurável,
   persistente, reversível e testado.
5. A licença do código upstream é GPL-2.0-only (LICENSE: versão 2, junho de 1991); os dados derivados do
   FlyWire têm avisos/termos próprios. Preserve os avisos e valide a licença
   aplicável ao redistribuir dados.

## Fontes primárias

- https://github.com/eonsystemspbc/fly-brain
- https://github.com/eonsystemspbc/fly-brain/blob/main/code/run_pytorch.py
- Shiu et al., modelo LIF baseado no conectoma adulto de Drosophila.
- Dorkenwald et al. (2024), FlyWire whole-brain connectome, Nature.
