# OpenHop iOS

Aplicativo SwiftUI para iPhone, compilado por GitHub Actions.

## O que já está implementado

- Painel de conectividade em tempo real com `Network.framework`.
- Identificação da interface (Wi-Fi, dados móveis ou Ethernet).
- Indicadores de rede de alto consumo e modo de dados reduzidos.
- Analisador local de cabeçalhos PE para inspecionar executáveis Windows.
- Interface nativa com abas Início, Analisar EXE e Sobre.

## Análise do executável fornecido

O arquivo `openhop.exe` é um executável Windows PE x86-64 empacotado com PyInstaller e Python 3.14. Foi possível recuperar os módulos Python e os recursos da interface do pacote. O programa original depende de componentes do Windows: WebView, serviços/processos em segundo plano, firewall, tarefas agendadas e o cliente `warp-cli`.

A inspeção também identificou automação de troca de IP após atingir limites gratuitos de um serviço externo. Essa função de contornar cotas/limites de uso não será portada. O projeto iOS mantém apenas recursos de diagnóstico e poderá receber recursos legítimos de privacidade que respeitem os controles dos serviços.

## Limitações do iOS

O iOS não executa binários PE/Windows nem oferece equivalentes diretos para serviços, firewall e tarefas agendadas do Windows. Um túnel VPN nativo exige uma implementação compatível com Network Extension e as permissões/entitlements apropriadas; não basta copiar o WARP CLI do Windows.

## Gerar IPA

O workflow **Build OpenHop IPA** compila em runner macOS e publica `OpenHop-unsigned.ipa` como artefato do GitHub Actions. O artefato é sem assinatura e precisa ser assinado para instalação no iPhone.

Workflow: `.github/workflows/build-openhop-ipa.yml`.
