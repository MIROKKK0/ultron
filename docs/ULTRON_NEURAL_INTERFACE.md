# ULTRON — interface neural inspirada em ficção científica

## Intenção

A evolução de JARVIS para FRIDAY e os sistemas de Tony Stark serve como referência narrativa de produto: um assistente começa respondendo, passa a entender contexto, coordena ferramentas, acompanha resultados e apresenta o estado do trabalho com clareza. O ULTRON adota esses princípios como inspiração, sem copiar interfaces, diálogos, ativos ou alegar capacidades fictícias.

## Linguagem visual

- Núcleo central: ponto de coordenação do ciclo do agente.
- Nós: unidades visuais abstratas de processamento.
- Conexões: caminhos de informação entre módulos.
- Pulsos: atividade animada ao longo das conexões.
- Anéis: camadas do núcleo e estado geral.
- Ciano: operação normal; vermelho: erro de conexão ou execução.

A visualização é procedural, original e desenhada com SwiftUI Canvas. Não usa vídeo, assets externos, partículas pesadas ou processamento de IA no dispositivo.

## Sincronização com o estado real

NeuralActivityView recebe BrainPhase e muda sua intensidade com base nos estados reais já emitidos pelo cliente:

| Estado | Representação |
| --- | --- |
| idle | núcleo em baixa atividade |
| connecting | conexões começam a pulsar |
| processing | maior frequência de disparos |
| responding | pulsos desaceleram enquanto a resposta chega |
| error | núcleo em vermelho e atividade reduzida |

A animação não representa pensamentos privados, tokens internos ou neurônios biológicos reais. Ela comunica apenas o estado operacional observável do app.

## Próximos passos

1. Expandir eventos do backend para etapas observáveis e verificáveis: planejamento, pesquisa, execução de ferramenta, crítica e síntese.
2. Mapear cada evento recebido para uma fase visual distinta, sem inventar atividade.
3. Adicionar testes de estado e acessibilidade; manter taxa de quadros e consumo medidos no iPhone 11 Pro.
4. Integrar o fluxo de credenciais e memória tipada em uma única linha de desenvolvimento depois da revisão das PRs abertas #45 e #46, que atualmente alteram os mesmos arquivos iOS/backend.
5. Manter treino generativo separado da interface: só promover checkpoints após avaliação PT-BR retida, comparação com o pai e zero regressões.

## Critério de aceite

A interface é aceita quando o workflow iOS compila o app para simulador e dispositivo, a animação reage às fases reais e o build IPA é publicado como artefato do GitHub Actions. Isso não equivale a IPA assinado ou instalado no iPhone.