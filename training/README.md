# ULTRON Tiny — núcleo linguístico experimental

Este diretório inicia o modelo linguístico próprio do ULTRON, sem provedores
externos, pesos pré-treinados ou tokenizador de terceiros.

## O que existe

- Tokenizador UTF-8 byte-level versionado (`ultron-byte-v1`), implementado aqui.
- Transformer decoder-only causal com pesos inicializados aleatoriamente.
- Treinamento CPU reproduzível com AdamW, clipping de gradiente e checkpoint.
- Corpus inicial autoral em português, incluído apenas para smoke training.

## Treinar

Instale as dependências isoladas:

```bash
python -m pip install -r training/requirements.txt
python -m training.train --steps 1000
```

O checkpoint será gravado em `artifacts/ultron-tiny.pt`. Não o coloque no
repositório sem avaliar tamanho, licença do corpus e métricas.

## Limites importantes

O corpus inicial é pequeno e didático. O checkpoint resultante **não será um
assistente competente**, não terá conhecimento geral e não equivale ao ChatGPT.
É uma primeira implementação verificável da arquitetura e do processo de
treinamento do zero. O backend de produção continua usando o decodificador
determinístico até que exista um checkpoint validado e um runtime de inferência
adequado.

O treinamento não deve ocorrer no serviço web de 512 MB. Execute-o em um runner
de CI ou máquina de treinamento separada. Antes de integrar inferência, medir
RSS, latência, qualidade, tamanho do checkpoint e comportamento sob carga.
