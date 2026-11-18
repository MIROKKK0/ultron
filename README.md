# ULTRON — IA Pessoal com Núcleo de Memória Próprio

ULTRON mantém um registro local, datado e verificável das conversas e decisões. O texto original permanece separado das interpretações produzidas por agentes. Provedores de IA são motores substituíveis; nenhum deles é dono da memória ou da identidade do ULTRON.

## Núcleo de memória

- Registro append-only em SQLite, com origem, autor, data UTC e hash SHA-256.
- Resumos, tags e interpretações ficam em registros derivados separados.
- Revisões acrescentam novas entradas e preservam versões anteriores.
- Relações explícitas entre entradas e busca textual local.
- Ledger encadeado por hashes, com verificação de integridade.
- Nenhuma chamada de rede é feita pelo módulo de memória.

## Modelo de execução

ULTRON usa um provedor compatível com a API OpenAI como mecanismo de inferência opcional. O núcleo, a memória e a trilha de auditoria continuam locais e independentes. A configuração não acopla o núcleo a um fornecedor específico.

## Setup

```bash
git clone https://github.com/MIROKKK0/ultron.git
cd ultron
pip install -r requirements.txt
cp .env.example .env
```

Configure `OPENAI_API_KEY` e, opcionalmente, `OPENAI_BASE_URL` e `ULTRON_MODEL` para um endpoint compatível. O provedor pode ser substituído sem migrar ou apagar `~/.ultron/memory.db`.

## Uso

```bash
python ultron.py
```

Comandos: `sair` encerra; `melhorar` propõe uma revisão do prompt de comportamento.

## Testes

```bash
python -m unittest discover -s tests -v
```

## Arquitetura

- `ultron.py`: loop conversacional, ferramentas e integração com o núcleo.
- `ultron_mind.py`: memória local, proveniência, derivações, relações e ledger.
- `~/.ultron/memory.db`: banco persistente.
- `~/.ultron/system_prompt.txt`: instruções comportamentais editáveis.

Detalhes técnicos: [docs/MIND_CORE.md](docs/MIND_CORE.md).

## Próximas camadas

Índice semântico local, importadores com deduplicação, backup criptografado, conectores consentidos e avaliação automatizada. Cada camada deve permanecer substituível e não pode sobrescrever o registro original.
