# ULTRON: evolução automática com validação

## O que a automação faz

- `ultron-autonomous-scout.yml`: auditoria leve e pesquisa de repositórios públicos a cada 10 minutos (`*/10 * * * *`). Verifica falhas recentes do Actions, issues abertas, marcadores TODO/FIXME e encontra pistas públicas sobre treinamento, tokenização e inferência. É somente leitura: não executa código externo, não altera branches nem abre PRs.
- `ios-build.yml`: compila um IPA iOS sem assinatura diariamente às 14:47 UTC (11:47 em UTC-3), além de compilar sob demanda e em alterações iOS. A compilação do simulador é ignorada no evento diário para economizar tempo.
- O app já oferece pesquisa web sob demanda: `/research sua consulta`, além do endpoint `/brain/research`. Os resultados incluem links; a pesquisa não significa que o ULTRON já tenha um LLM capaz de sintetizar qualquer assunto com qualidade humana.

O workflow `.github/workflows/ultron-autonomous-evolution.yml` separa validação de PR do treinamento diário real:

1. Em PR, reproduz o classificador de intenções, executa a suíte de testes e faz apenas um smoke training curto no corpus didático pequeno. Esse checkpoint de smoke não é publicado como modelo diário.
2. Na branch padrão, procura primeiro o último checkpoint diário bem-sucedido; se não houver, tenta o último checkpoint semanal BPE PT-BR.
3. Exige que o checkpoint, o tokenizer e os splits licenciados train/validation/test estejam presentes e compatíveis. Se não houver baseline PT-BR, registra `waiting_for_validated_ptbr_baseline` e não finge evolução treinando repetidamente no corpus de 1,8 KB.
4. Continua os pesos com o mesmo BPE, corpus e splits, mede validação e teste em janelas comparáveis e mantém o checkpoint pai quando o candidato regredir.
5. Recarrega o checkpoint, verifica geração em CPU, produz amostras fixas, mede latência e RSS do runner e guarda a linhagem em artefatos.
6. O treinamento diário não promove pesos para produção, não altera código, não faz merge e não faz deploy.

O workflow separado `ptbr-pretraining.yml` prepara corpus de livros brasileiros com licença declarada CC0-1.0, cria splits 80/10/10 por hash, treina BPE próprio na primeira execução e executa pré-treino maior. O artefato agora inclui tokenizer, checkpoint, manifesto, proveniência e os três splits para que o ciclo diário continue o mesmo experimento. O corpus cresce gradualmente até o limite configurado. O otimizador é reiniciado a cada ciclo: os pesos continuam, mas o estado do otimizador não é retomado. O candidato semanal é comparado com o checkpoint pai em validação e teste; se regredir além da tolerância, o checkpoint anterior é restaurado para o próximo ciclo.
## Limites deliberados

- Todos os eventos `schedule` só rodam quando o arquivo está na branch padrão `main`; schedules não são ativados enquanto as alterações estiverem apenas neste PR/branch. O scout também tem `push` para validar sua execução antes do merge.
- O cron de 10 minutos é aceito pelo GitHub (o menor intervalo permitido é 5 minutos), mas é best-effort: pode atrasar ou ser ignorado em períodos de carga. Não é um relógio garantido.
- Como o repositório é público, runners padrão hospedados pelo GitHub não consomem a franquia mensal de minutos; isso não elimina limites de concorrência, atrasos ou custos de armazenamento. A frequência gera até 144 execuções diárias, então o scout é deliberadamente curto e não treina o modelo a cada ciclo.
- O IPA diário é um artefato sem assinatura, pronto para ser assinado pelo SideStore; não é instalado automaticamente no iPhone nem substitui teste físico.

- Um checkpoint experimental nunca substitui automaticamente pesos de produção.
- O workflow de treinamento não altera código, não faz merge e não faz deploy. O scout de 10 minutos é somente leitura.
- A continuação diária/semanal depende da retenção do artefato anterior (14 dias) e da compatibilidade da arquitetura/tokenizador. O pré-treino semanal pode iniciar do zero quando ainda não existe checkpoint; o treino diário aguarda um baseline semanal validado em vez de treinar o corpus didático. Se houver incompatibilidade, falha em vez de carregar pesos incorretos.
- O benchmark de RAM/latência é medido no runner Linux; não representa o iPhone nem o serviço de hospedagem.
- A execução diária de `schedule` só ocorre quando o workflow está presente na branch padrão (`main`). Execuções de PR validam a proposta, mas não ativam o cron.
- O modelo atual é pequeno, treinado do zero e limitado pelo volume e diversidade do corpus. Uma perda menor no mesmo corpus não prova capacidade geral, raciocínio ou equivalência ao ChatGPT.
- O dataset de livros declara CC0-1.0, mas o próprio cartão informa que não foi sanitizado de PII e pode conter nomes, contatos e vieses. A limpeza por regex não é garantia de anonimização; revisar amostras e filtrar conteúdo antes de distribuir artefatos.

## Como evoluir com segurança

A próxima etapa é ampliar o corpus com fontes permitidas e documentar licenças, manter conjuntos separados de treino/validação/teste, criar avaliações de comportamento em português e comparar cada candidato com a versão estável. Só promover um checkpoint se ele melhorar tarefas retidas sem regressões de segurança, qualidade, latência e memória. Guardar sempre o checkpoint anterior para rollback.

Para autoevolução de código, o agente deve operar em branch isolada, propor um PR pequeno, executar CI e nunca obter permissão de merge/deploy automático. Dados de conversas privadas não devem ser usados como corpus de treino sem consentimento explícito e anonimização adequada.
