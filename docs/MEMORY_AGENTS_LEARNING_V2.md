# ULTRON — memória vetorial, especialistas e aprendizagem avaliada

## Memória semântica e índice local

As memórias continuam separadas por instalação e tipo: episódica, semântica e procedural. O índice `LocalVectorIndex` armazena vetores esparsos em SQLite/PostgreSQL, sem serviço vetorial externo ou dependência pesada. O encoder atual combina tokens e n-gramas de caracteres com hashing determinístico; isso oferece similaridade lexical aproximada, não embeddings neurais nem compreensão semântica profunda. A interface é substituível por um encoder neural genuinamente local quando o modelo próprio produzir embeddings validados.

Toda consulta filtra por `owner_id`; exclusão remove o vetor junto com a memória. Vetores carregam versão do encoder para permitir reindexação controlada.

## Importação histórica

A rota autenticada `POST /v2/memory/import` recebe exportação explícita do cliente, registra somente mensagens user/assistant e deduplica por hash de origem. Não lê a tabela legada global `conversations`, porque ela não tem escopo de instalação e misturá-la poderia expor histórico de outra pessoa. Importações repetidas não duplicam entradas.

## Especialistas

`backend/specialist_agents.py` mantém handlers determinísticos e independentes para planner, solver, critic, memory retriever, memory curator e evaluator. O curator só propõe fatos semânticos e conserva IDs das fontes; não grava fatos inferidos sem aprovação.

## Planejamento e aprendizagem

O planejador mantém decomposição, dependências e critérios observáveis. `backend/learning_gate.py` compara candidato e baseline usando exatamente o mesmo conjunto congelado, rejeitando regressão por caso, mesmo quando a média geral sobe. Feedback não altera pesos de modelos externos.

## Limites de inferência

O núcleo, identidade, banco, indexador, especialistas e critérios de publicação não dependem de Gemini nem de outro fornecedor. Um modelo generativo pode ser desligado ou trocado sem migrar a memória. O encoder vetorial desta versão é local e leve; não deve ser anunciado como embedding semântico neural.
