# OpenHop iOS

Aplicativo SwiftUI para iPhone, com pipeline de compilação IPA no GitHub Actions.

## Estado do porte

O arquivo fornecido, `openhop.exe`, é um executável Windows PE x86-64. iOS não executa binários PE/Windows. Sem o código-fonte original, não é possível reproduzir as funções do OpenHop apenas convertendo o EXE.

Esta primeira versão é um inspetor local: permite selecionar o EXE e valida a assinatura MZ/PE e a arquitetura. Não executa nem substitui o programa Windows.

## Gerar IPA

O workflow **Build OpenHop IPA** compila em um runner macOS e publica `OpenHop-unsigned.ipa` como artefato do GitHub Actions.

O IPA é sem assinatura. Para instalar no iPhone, assine com um certificado/perfil válido ou use o fluxo de assinatura do SideStore.

## Próximo passo do porte real

Adicionar o código-fonte original e suas dependências, ou especificar/reimplementar as funções necessárias em Swift. O EXE isolado não contém os fontes necessários para essa etapa.

Build workflow: `.github/workflows/build-openhop-ipa.yml`.
