# ULTRON — roteiro científico para uma IA centrada no FlyBrain

Status: implementação integrada em andamento. O módulo de codificação esparsa, associação modulada por recompensa, persistência de checkpoint e calibração de estratégia por feedback foram adicionados nesta branch; validação de CI ainda pendente. Os itens restantes continuam pendentes.

## Estado comprovado

- O branch `feat/ultron-core-assistant` contém o microcircuito LIF de 48 neurônios, memória lexical, decodificador português determinístico e feedback que calibra prioridades de estratégias em até ±15%.
- O bridge `backend/flywire_runtime.py` consegue carregar e simular o modelo PyTorch do FlyWire FAFB v783 em CI. A validação já executada no GitHub Actions confirmou 138.639 neurônios modelados e dois estímulos de demonstração (`sugar` e `p9`).
- Isso é uma simulação neural sensório-motora. Não é uma rede treinada para linguagem, raciocínio geral ou consciência.
- O serviço Render Free ainda não carrega o conectoma completo em produção. O teste do GitHub Actions não significa que o backend de produção esteja executando os 138 mil neurônios.

## O que falta para o cérebro virar o núcleo de uma IA útil

### 1. Codificador de entrada (parcial — primeira versão adicionada)
Foi adicionado um codificador lexical esparso determinístico de 256 dimensões. Ele não é embedding semântico e ainda não generaliza significado; é uma ponte inicial testável entre texto e atividade.
Criar uma representação estruturada de texto, áudio, imagem e resultados da web. O codificador precisa mapear intenção, entidades, relações, contexto e incerteza para padrões de atividade neural. Não basta mapear palavras isoladas para neurônios escolhidos manualmente.

Critérios de aceitação:
- conjunto de dados de pares entrada/representação;
- avaliação de similaridade semântica e generalização para frases nunca vistas;
- teste de ablação demonstrando que a saída muda quando o estado neural muda.

### 2. Modelo neural completo e validado (parcial)
Manter o FlyWire como fonte anatômica, mas verificar conectividade, sinais excitatórios/inibitórios, delays, regiões e parâmetros. O modelo Shiu et al. é LIF e prevê transformações sensório-motoras; não inclui todos os mecanismos biológicos.

Critérios:
- reproduzir benchmarks publicados de alimentação, grooming e circuitos sensoriais;
- comparar spikes, taxas de disparo e neurônios recrutados com resultados de referência;
- registrar versão do dataset, checksums, parâmetros e resultados de cada experimento.

### 3. Memória neural e aprendizagem (parcial — primeira versão adicionada)
Foi adicionada memória associativa pré/pós-atividade modulada por recompensa, com decaimento, limites de peso, recall e checkpoint no banco. O feedback do app ajusta prioridades de estratégia dentro de limites. Ainda não há plasticidade dos pesos FlyWire.
A memória atual é uma tabela de texto com busca lexical. O feedback atual ajusta apenas prioridades de planner/solver/critic. Não há plasticidade sináptica.

A pesquisa sobre o mushroom body da mosca aponta mecanismos relevantes: células Kenyon, neurônios dopaminérgicos, neurônios de saída, reforço, erro de previsão, plasticidade e memórias com estabilidade diferente. A próxima implementação deve usar uma regra de plasticidade de três fatores (atividade pré/pós-sináptica + sinal modulador), com limites, decaimento, consolidação e replay. Não se deve atualizar os 15 milhões de pesos sem experimento controlado.

Critérios:
- aprender associações em tarefas simples de estímulo/recompensa;
- medir retenção, esquecimento, transferência e interferência;
- comparar contra uma baseline sem plasticidade;
- permitir exportar, restaurar e auditar o estado aprendido.

### 4. Decodificador de saída (pendente)
O decodificador atual continua determinístico e baseado em regras; não foi treinado para ler padrões neurais e gerar linguagem.
Atividade neural não é texto. Treinar um readout que transforme padrões populacionais em intenções, ações e respostas. O readout precisa ser avaliado em dados separados dos usados no treino. Sem essa ponte, o LIF pode simular spikes mas não conversar abertamente.

### 5. Ciclo cognitivo e ferramentas (parcial)
O chat, pesquisa, core neural e decodificador estão conectados em um fluxo; especialistas paralelos continuam sendo perspectivas heurísticas executadas pelo decodificador local, não agentes de linguagem independentes.
O planner/solver/critic atual é uma orquestração heurística, não três inteligências independentes. O próximo ciclo deve ser:
1. codificar a solicitação;
2. recuperar memória relevante;
3. ativar o cérebro;
4. decodificar hipóteses/intenções;
5. selecionar ferramenta ou ação;
6. observar o resultado;
7. avaliar erro e recompensa;
8. consolidar apenas a aprendizagem aprovada.

Pesquisa web é uma ferramenta de percepção externa, não deve ser apresentada como se o conectoma tivesse conhecimento da internet. A busca deve guardar consulta, URLs, data, trechos e evidência, e separar fatos de inferências.

### 6. Autoaperfeiçoamento seguro (parcial)
Feedback real do usuário calibra prioridades de estratégia, com limite de 10 avaliações por IP/hora e ajuste máximo de ±15%. O módulo associativo tem aprendizagem experimental por recompensa. Não há autoalteração de código nem treino de pesos do conectoma.
A evolução atual é calibração limitada por feedback. Para evoluir de verdade, criar um ciclo de experimentos:
- detectar falhas recorrentes;
- criar hipótese e métrica antes de alterar;
- gerar branch experimental;
- executar testes e benchmarks fixos;
- comparar com a versão anterior;
- promover somente se melhorar sem regressões;
- manter rollback e histórico de pesos/dados.

O agente não deve reescrever nem implantar o próprio código de produção sem revisão e testes.

### 7. Infraestrutura (pendente)
O runtime completo precisa de benchmark de RAM, CPU/GPU, tempo de inicialização e latência sustentada. O dataset upstream inclui arquivos grandes e a matriz esparsa gerada ocupa centenas de MB antes da memória de execução. O Render Free não deve ser tratado como host validado para o cérebro completo.

O iPhone 11 Pro deve ser tratado inicialmente como cliente SwiftUI. Executar o conectoma inteiro no telefone exigiria uma implementação nativa otimizada, armazenamento local dos dados, medição térmica e de memória; não é uma consequência automática de gerar um IPA.

### 8. Segurança do acesso sem token (bloqueador antes de publicar)
Não colocar um segredo estático dentro do IPA. Para endpoints públicos, usar limites compartilhados no banco, quotas por instalação, proteção contra abuso e isolamento de memória/conversas por instalação. A opção nativa de integridade é Apple App Attest, com desafio de uso único, atestado validado no servidor e assertions assinadas. Até concluir isso, não abrir endpoints que leiam/escrevam memória privada ou alterem aprendizagem global sem autenticação.

Nota de implementação: a rota pública do chat está deliberadamente sem memória persistente até existir isolamento de dados por instalação. Não remover essa proteção para 'fazer memória funcionar' sem concluir App Attest/identidade e testes de privacidade.

## Ordem recomendada

1. Fechar privacidade, identidade de instalação, rate limits compartilhados e testes de API.
2. Ativar pesquisa web com fontes, timeout, cache e validação dos links.
3. Integrar o runtime FlyWire ao ambiente de produção com benchmark reproduzível.
4. Implementar codificador semântico e decodificador de saída com datasets de avaliação.
5. Implementar memória episódica/semântica e plasticidade modulada inspirada no mushroom body.
6. Criar benchmarks de aprendizagem contínua, generalização e esquecimento catastrófico.
7. Só então declarar o ULTRON como IA neural de linguagem funcional; nunca confundir simulação de conectoma com inteligência geral.

## Referências científicas e técnicas

- Shiu et al. (2024), *A Drosophila computational brain model reveals sensorimotor processing*, Nature 634:210–219, https://doi.org/10.1038/s41586-024-07763-9
- Dorkenwald et al. (2024), *Neuronal wiring diagram of an adult brain*, Nature 634:124–138, https://doi.org/10.1038/s41586-024-07558-y
- Modi, Shuai & Turner (2020), *The Drosophila Mushroom Body: From Architecture to Algorithm in a Learning Circuit*, Annual Review of Neuroscience 43:465–484, https://doi.org/10.1146/annurev-neuro-080317-0621333
- Bennett, Philippides & Nowotny (2021), *Learning with reinforcement prediction errors in a model of the Drosophila mushroom body*, Nature Communications 12:2569, https://doi.org/10.1038/s41467-021-22592-4
- Apple, *Validating apps that connect to your server* (App Attest): https://developer.apple.com/documentation/devicecheck/validating-apps-that-connect-to-your-server
