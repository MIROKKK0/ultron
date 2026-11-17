# ULTRON Tiny — Transformer generativo experimental

Este subprojeto é uma implementação própria e pequena de um Transformer
decoder-only. Todos os pesos começam aleatórios; não há modelos pré-treinados,
provedores de IA externos ou tokenizador de terceiros.

## Componentes
- Tokenizador UTF-8 byte-level versionado (`ultron-byte-v1`).
- Atenção causal multi-head, blocos pre-LN e previsão do próximo byte.
- Treino CPU reproduzível com AdamW e clipping de gradiente.
- Corpus autoral curto em português para smoke training.

## Treinar
```bash
python -m pip install -r training/generative/requirements.txt
python -m training.generative.train --steps 1000
```

O checkpoint vai para `artifacts/ultron-tiny.pt`. O backend principal continua
usando o classificador de intenções próprio e o fallback determinístico até que
um modelo generativo tenha avaliação independente e um runtime de inferência
compatível com a memória disponível.

## Limites
O corpus inicial é pequeno e didático. O resultado não tem conhecimento geral,
não é um assistente competente e não equivale ao ChatGPT. O treinamento não
deve acontecer no serviço web de 512 MB. Antes de integrar inferência, medir
perplexidade, qualidade em português, segurança, latência, RSS e carga concorrente.
