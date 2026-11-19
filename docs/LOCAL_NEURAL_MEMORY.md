# Memória neural local — marco 1

## Arquitetura

- O encoder é o próprio ULTRON Tiny Transformer, inicializado e treinado pelo projeto.
- A representação é o mean-pooling normalizado dos estados ocultos finais.
- O checkpoint é carregado de disco local; nenhuma chamada de embedding é enviada a Gemini ou outro provedor.
- Cada vetor registra uma versão que inclui o SHA-256 do checkpoint.
- Quando a versão muda, `index_missing` reprocessa memórias antigas por instalação.
- A migração preserva o texto, o ID, a proveniência e o timestamp da memória original.

## Ativação

Instale as dependências opcionais de treino e defina:

```bash
pip install -r training/generative/requirements.txt
ULTRON_MEMORY_ENCODER=neural
ULTRON_NEURAL_EMBEDDINGS_CHECKPOINT=/caminho/ultron-tiny.pt
```

Sem checkpoint, o modo lexical existente permanece disponível. Se o modo neural
for explicitamente selecionado e o checkpoint estiver ausente ou inválido, o
sistema falha fechado em vez de enviar dados a um serviço externo.

## Limites desta etapa

O Transformer atual foi treinado principalmente para previsão do próximo token.
Mean-pooling desses estados não prova, por si só, qualidade semântica. Este marco
adiciona a integração técnica e a persistência versionada; o benchmark de paráfrases
e o fine-tuning contrastivo próprio são gates obrigatórios antes de declarar a
busca semântica pronta para produção. O checkpoint de treino não é distribuído
nem promovido automaticamente por este PR.
