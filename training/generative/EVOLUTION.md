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
