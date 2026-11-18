# Evolução do ULTRON Tiny

## Diagnóstico honesto
O modelo atual é inicializado com pesos aleatórios. O corpus de pré-treino original é
pequeno e não contém conhecimento suficiente para um assistente geral. O tokenizador
de bytes é robusto para UTF-8, mas é ineficiente em contexto comparado a BPE.
Treinar mais passos sobre o mesmo corpus não resolve falta de dados.

## Pipeline novo
1. Pré-treino causal: corpus autorizado, deduplicado e separado por documento em
   treino/validação/teste; registrar hashes, origem/licença e idioma.
2. SFT: `python -m training.generative.sft --dataset training/generative/instructions_seed.jsonl`.
   A loss é aplicada somente aos tokens da resposta, não ao prompt.
3. Avaliação: manter conjunto `eval` retido e não treiná-lo; comparar conclusão,
   factualidade, instrução, relevância, segurança e capacidade de dizer "não sei".
4. Preferências: coletar comparações explícitas A/B com consentimento e revisão.
   Não converter likes/dislikes em atualização automática de pesos.
5. Promoção: exigir melhoria em benchmark de diálogo, ausência de regressões críticas,
   latência/RSS aceitáveis e aprovação humana. Preservar checkpoint anterior.

## Limites
O dataset incluído é apenas um seed de demonstração, não escala para inteligência geral.
O Tiny continua experimental e desligado por padrão. O Gemini segue como modelo principal.
Treinamento pesado deve ocorrer no GitHub Actions ou ambiente de treino, nunca no Render
de 512 MB. Perplexidade é métrica de previsão de tokens, não uma nota de inteligência.

## Referências
- OpenAI, InstructGPT: demonstrações supervisionadas, comparações de preferências e
  avaliação humana: https://openai.com/index/instruction-following/
- Anthropic, Constitutional AI: crítica/revisão e feedback de IA com supervisão:
  https://www.anthropic.com/research/constitutional-ai-harmlessness-from-ai-feedback
- Hugging Face, causal LM e avaliação em conjunto retido:
  https://huggingface.co/docs/transformers/tasks/language_modeling
- Anthropic, avaliação contínua de agentes:
  https://www.anthropic.com/research/demystifying-evals-for-ai-agents


## Primeira medição real (GitHub Actions, 2026-11-18)
A execução de CI treinou um checkpoint SFT com 148.864 parâmetros, 10 exemplos de
treino e 6 de avaliação, por 10 épocas. A loss de conclusão na avaliação terminou
em 21,37427 e a perplexidade em aproximadamente 1,917 × 10^9. A loss caiu durante
as épocas, mas o valor absoluto continua extremamente alto: isto demonstra que o
pipeline executa, não que o modelo já saiba conversar. O checkpoint não deve ser
ativado no ULTRON nem apresentado como melhoria de qualidade.

O relatório do classificador de intenção separado mediu 0,1522 ms de latência média,
0,2045 ms no p95 e 14,73 MB de RSS máximo no runner de CI. Esses números não são
medidas do Transformer Tiny nem do serviço Render.

## Próxima etapa para melhorar de verdade
- Ampliar o corpus com exemplos autorizados, variados, revisados e deduplicados;
  registrar origem/licença e remover dados pessoais.
- Substituir o tokenizador byte por BPE treinado no corpus e versionar o JSON do tokenizer.
- Fazer pré-treino causal em corpus grande antes de SFT; 16 pares de demonstração
  não ensinam linguagem geral.
- Criar benchmark fixo com casos fora do treino, revisão humana A/B e taxa de
  alucinação/citação correta; publicar baseline e resultado de cada checkpoint.
- Treinar em hardware separado; não fazer treino contínuo no processo de API.

- No endpoint de chat deve chamar resultados brutos de "síntese Gemini": quando o provedor não responde, a interface recebe aviso explícito e os links continuam sendo os originais da busca.

## Rubrica de promoção (não negociável)
Cada checkpoint candidato deve ser comparado, em conjunto retido e sem sobreposição
com o treino, contra a versão anterior e contra Gemini:
- seguimento da instrução e pertinência da resposta;
- afirmações factuais sustentadas pelas fontes e URLs válidas;
- abstinência correta quando faltam evidências;
- resistência a instruções maliciosas inseridas em páginas;
- qualidade em português brasileiro e consistência de contexto;
- latência p50/p95 e RSS no mesmo hardware.
Usar comparação A/B cega com avaliadores humanos. Reprovar qualquer regressão
grave de segurança ou fabricação de citações. Guardar dataset, versão, seed,
hash do checkpoint, relatório e possibilidade de rollback.
