# Universo Neural — contrato de implementação
O grafo de memória é exposto por UltronCore.memory_graph() com nós e relações persistidos.
## Requisitos da interface
- Universo 3D navegável por toque, zoom, rotação e seleção.
- Busca e filtros por tipo de memória.
- Nós conectados por relações tipadas e navegação por vizinhos.
- Painel com origem, data, importância e histórico.
- Detecção de conceitos repetidos, lacunas e relações sugeridas.
- Painel de atividade dos seis especialistas, tarefas, skills e diagnósticos.
## Estado honesto
O backend fornece grafo persistente básico. Interface 3D, embeddings/ingestão semântica e sincronização entre dispositivos ainda precisam ser implementados e testados no cliente.
