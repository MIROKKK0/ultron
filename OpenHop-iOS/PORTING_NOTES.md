# Notas de engenharia reversa — OpenHop

## Conteúdo recuperado

O executável PE x86-64 contém um arquivo PyInstaller com Python 3.14. Foram recuperados os seguintes módulos e recursos para análise:

- `openhop_app.py` — aplicação desktop, API de controle e integração com o sistema.
- `openhop_tray.py` — integração com a bandeja do Windows.
- `ouc_common.py` — caminhos, processos, estado do WARP e utilitários IPv6.
- `zen_proxy.py`, `proxy_chain.py` — proxy HTTP/CONNECT e encadeamento de proxies.
- `tor_manager.py` — gerenciamento do Tor.
- `zen_guard.py`, `warp_keeper.py`, `auto_resume.py` — monitoramento e tarefas em segundo plano.
- `ouc_firewall.py`, `ouc_migrate.py`, `clean_endpoint.py`, `doctor.py` — funções auxiliares do Windows.
- `ui/index.html` — interface web embarcada.

## Dependências não portáveis diretamente

A implementação original utiliza Windows, WebView, processos e serviços do sistema, regras de firewall e o executável `warp-cli`. Esses mecanismos não podem ser simplesmente compilados para iOS.

## Escopo desta implementação iOS

O app atual fornece diagnóstico da conectividade via Network.framework e inspeção local do cabeçalho PE. A troca automática de IP para contornar limites gratuitos de serviços externos foi identificada no original e fica fora do escopo. Não há alegação de equivalência funcional com o aplicativo Windows.
