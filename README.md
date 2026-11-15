# ULTRON

Assistente pessoal em português, com aplicativo nativo para iPhone, API HTTP, memória persistente e integração opcional com IA.

## O que já está no projeto

- App nativo SwiftUI com chat, status de conexão e configuração do servidor.
- Cliente HTTPS para conversar com a API.
- Backend FastAPI com memória SQLite.
- Calculadora segura e comandos locais.
- Integração opcional com OpenAI Responses API.
- Testes Python e workflows de CI/build no GitHub Actions.

## Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python ultron.py
```

A API fica em `http://localhost:8000`; a documentação interativa fica em `/docs`.

Defina `OPENAI_API_KEY` no ambiente do servidor para habilitar respostas via modelo. Não coloque chaves no app iOS nem em commits.

## App iOS

O projeto Xcode é gerado com XcodeGen:

```bash
brew install xcodegen
xcodegen generate
open ULTRON.xcodeproj
```

O workflow `ULTRON iOS Build` compila o app para o simulador iOS em um runner macOS do GitHub. No app, informe o endereço HTTPS público do backend em Configurações.

## IPA para iPhone

A compilação do simulador não gera um IPA instalável no iPhone. Para distribuir um IPA assinado, o workflow precisa de certificado Apple e provisioning profile válidos, guardados como GitHub Secrets. Não envie certificados, senhas ou chaves nesta conversa.

## Segurança

O ULTRON não executa comandos arbitrários, não tenta invadir sistemas e não contorna autenticação ou assinaturas. Ações externas ou irreversíveis devem exigir confirmação explícita.

## Próximas etapas

- Hospedar o backend em um endpoint HTTPS estável.
- Validar o build iOS no GitHub Actions.
- Configurar assinatura de dispositivo e exportação IPA.
- Adicionar voz, notificações e integrações nativas após validação.
