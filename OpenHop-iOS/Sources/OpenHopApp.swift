import SwiftUI
import UniformTypeIdentifiers
import Network

@main
struct OpenHopApp: App {
    var body: some Scene {
        WindowGroup { ContentView() }
    }
}

@MainActor
final class NetworkStatus: ObservableObject {
    @Published private(set) var connected = false
    @Published private(set) var interface = "Verificando…"
    @Published private(set) var expensive = false
    @Published private(set) var constrained = false

    private let monitor = NWPathMonitor()
    private let queue = DispatchQueue(label: "com.mirokkk0.openhop.network-monitor")

    init() {
        monitor.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                self?.connected = path.status == .satisfied
                self?.expensive = path.isExpensive
                self?.constrained = path.isConstrained
                if path.usesInterfaceType(.wifi) {
                    self?.interface = "Wi-Fi"
                } else if path.usesInterfaceType(.cellular) {
                    self?.interface = "Dados móveis"
                } else if path.usesInterfaceType(.wiredEthernet) {
                    self?.interface = "Ethernet"
                } else if path.status == .unsatisfied {
                    self?.interface = "Sem conexão"
                } else {
                    self?.interface = "Outra interface"
                }
            }
        }
        monitor.start(queue: queue)
    }

    deinit { monitor.cancel() }
}

struct ContentView: View {
    @StateObject private var network = NetworkStatus()
    @State private var showingPicker = false
    @State private var fileName = "Nenhum arquivo selecionado"
    @State private var report = "Selecione um executável para analisar sua assinatura PE."
    @State private var isPE = false

    var body: some View {
        TabView {
            dashboard
                .tabItem { Label("Início", systemImage: "square.grid.2x2.fill") }
            analyzer
                .tabItem { Label("Analisar EXE", systemImage: "doc.text.magnifyingglass") }
            about
                .tabItem { Label("Sobre", systemImage: "info.circle") }
        }
        .tint(.cyan)
    }

    private var dashboard: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 18) {
                    VStack(spacing: 8) {
                        Image(systemName: "network")
                            .font(.system(size: 44, weight: .medium))
                            .foregroundStyle(.cyan)
                        Text("OpenHop")
                            .font(.largeTitle.bold())
                        Text("Painel de diagnóstico de rede")
                            .foregroundStyle(.secondary)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.top, 24)

                    VStack(alignment: .leading, spacing: 14) {
                        HStack {
                            Label("Conectividade", systemImage: "antenna.radiowaves.left.and.right")
                                .font(.headline)
                            Spacer()
                            Circle()
                                .fill(network.connected ? .green : .red)
                                .frame(width: 10, height: 10)
                            Text(network.connected ? "Conectado" : "Sem internet")
                                .font(.subheadline.weight(.semibold))
                        }
                        Divider()
                        infoRow("Interface", network.interface)
                        infoRow("Rede de alto consumo", network.expensive ? "Sim" : "Não")
                        infoRow("Modo de dados reduzidos", network.constrained ? "Ativo" : "Inativo")
                    }
                    .padding()
                    .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 18))

                    VStack(alignment: .leading, spacing: 8) {
                        Label("Diagnóstico seguro", systemImage: "checkmark.shield")
                            .font(.headline)
                        Text("O app monitora o estado da conexão do iPhone. Ele não altera a rede de outros apps, não instala VPN e não modifica limites de serviços externos.")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding()
                    .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 18))
                }
                .padding()
            }
            .background(Color(uiColor: .systemGroupedBackground))
            .navigationTitle("OpenHop")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private var analyzer: some View {
        NavigationStack {
            VStack(spacing: 18) {
                Image(systemName: "doc.text.magnifyingglass")
                    .font(.system(size: 48))
                    .foregroundStyle(.cyan)
                Text("Analisador PE")
                    .font(.title2.bold())
                VStack(alignment: .leading, spacing: 12) {
                    Text(fileName).font(.headline).lineLimit(2)
                    Text(report)
                        .font(.body)
                        .textSelection(.enabled)
                    if isPE {
                        Label("Executável Windows reconhecido", systemImage: "checkmark.seal.fill")
                            .foregroundStyle(.green)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
                .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 18))
                Button {
                    showingPicker = true
                } label: {
                    Label("Selecionar arquivo .exe", systemImage: "folder")
                        .frame(maxWidth: .infinity)
                        .padding()
                }
                .buttonStyle(.borderedProminent)
                Text("A análise é local. O arquivo não é enviado para nenhum servidor.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                Spacer()
            }
            .padding()
            .background(Color(uiColor: .systemGroupedBackground))
            .navigationTitle("Analisar EXE")
            .fileImporter(isPresented: $showingPicker, allowedContentTypes: [.data], allowsMultipleSelection: false) { result in
                inspect(result)
            }
        }
    }

    private var about: some View {
        NavigationStack {
            List {
                Section("Sobre o porte") {
                    LabeledContent("Versão", value: "Prévia iOS")
                    LabeledContent("Plataforma", value: "iPhone / iOS 16+")
                    LabeledContent("Código original", value: "Python + interface WebView")
                }
                Section("Limitações técnicas") {
                    Text("O executável original usa componentes específicos do Windows, como serviços, firewall, tarefas agendadas e o cliente de linha de comando do WARP. Eles não podem ser executados diretamente no iOS.")
                    Text("A troca automática de IP para contornar limites gratuitos de serviços externos não será reproduzida. O app pode oferecer diagnóstico e recursos legítimos de privacidade, sem burlar cotas ou controles de acesso.")
                }
                Section("Privacidade") {
                    Text("O monitor de rede usa Network.framework e exibe apenas o estado da conexão informado pelo próprio iOS.")
                }
            }
            .navigationTitle("Sobre")
        }
    }

    private func infoRow(_ title: String, _ value: String) -> some View {
        HStack {
            Text(title).foregroundStyle(.secondary)
            Spacer()
            Text(value).fontWeight(.medium)
        }
        .font(.subheadline)
    }

    private func inspect(_ result: Result<[URL], Error>) {
        do {
            guard let url = try result.get().first else { return }
            let access = url.startAccessingSecurityScopedResource()
            defer { if access { url.stopAccessingSecurityScopedResource() } }

            let handle = try FileHandle(forReadingFrom: url)
            defer { try? handle.close() }
            let header = try handle.read(upToCount: 64) ?? Data()
            fileName = url.lastPathComponent

            guard header.count >= 64, header[0] == 0x4D, header[1] == 0x5A else {
                isPE = false
                report = "Assinatura MZ ausente. O arquivo não foi reconhecido como executável PE."
                return
            }

            let offset = Int(header[0x3C]) | (Int(header[0x3D]) << 8) |
                (Int(header[0x3E]) << 16) | (Int(header[0x3F]) << 24)
            let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
            let size = (attributes[.size] as? NSNumber)?.int64Value ?? 0
            guard offset >= 0, Int64(offset) + 6 <= size else {
                isPE = false
                report = "O cabeçalho PE aponta para uma posição inválida."
                return
            }

            try handle.seek(toOffset: UInt64(offset))
            let pe = try handle.read(upToCount: 6) ?? Data()
            guard pe.count == 6, pe[0] == 0x50, pe[1] == 0x45,
                  pe[2] == 0, pe[3] == 0 else {
                isPE = false
                report = "Cabeçalho PE inválido."
                return
            }

            let machine = UInt16(pe[4]) | (UInt16(pe[5]) << 8)
            let architecture: String
            switch machine {
            case 0x8664: architecture = "x86-64 (AMD64)"
            case 0x14C: architecture = "x86 (32 bits)"
            case 0xAA64: architecture = "ARM64"
            default: architecture = String(format: "desconhecida (0x%04X)", machine)
            }
            isPE = true
            report = "Cabeçalho PE válido. Arquitetura: \(architecture). Tamanho: \(ByteCountFormatter.string(fromByteCount: size, countStyle: .file))."
        } catch {
            isPE = false
            report = "Falha ao abrir o arquivo: \(error.localizedDescription)"
        }
    }
}
