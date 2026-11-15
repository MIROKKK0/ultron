import SwiftUI
import UniformTypeIdentifiers

@main
struct OpenHopApp: App {
    var body: some Scene {
        WindowGroup { ContentView() }
    }
}

struct ContentView: View {
    @State private var showingPicker = false
    @State private var fileName = "Nenhum arquivo selecionado"
    @State private var report = "Selecione openhop.exe para conferir a arquitetura e os cabeçalhos."
    @State private var isPE = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 22) {
                Image(systemName: "cpu")
                    .font(.system(size: 54, weight: .medium))
                    .foregroundStyle(.tint)
                Text("OpenHop iOS")
                    .font(.largeTitle.bold())
                Text("Análise local do executável")
                    .foregroundStyle(.secondary)
                VStack(alignment: .leading, spacing: 10) {
                    Text(fileName).font(.headline).lineLimit(2)
                    Text(report).font(.body)
                        .textSelection(.enabled)
                    if isPE {
                        Label("Executável Windows PE reconhecido", systemImage: "checkmark.seal.fill")
                            .foregroundStyle(.green)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
                .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 16))
                Button {
                    showingPicker = true
                } label: {
                    Label("Selecionar openhop.exe", systemImage: "doc")
                        .frame(maxWidth: .infinity)
                        .padding()
                }
                .buttonStyle(.borderedProminent)
                Text("O iOS não executa arquivos .exe. Esta versão inspeciona o arquivo; o porte das funções originais exige o código-fonte ou uma reimplementação.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                Spacer()
            }
            .padding()
            .navigationTitle("OpenHop")
            .navigationBarTitleDisplayMode(.inline)
            .fileImporter(isPresented: $showingPicker, allowedContentTypes: [.data], allowsMultipleSelection: false) { result in
                inspect(result)
            }
        }
    }

    private func inspect(_ result: Result<[URL], Error>) {
        do {
            guard let url = try result.get().first else { return }
            let access = url.startAccessingSecurityScopedResource()
            defer { if access { url.stopAccessingSecurityScopedResource() } }
            let handle = try FileHandle(forReadingFrom: url)
            defer { try? handle.close() }
            let data = try handle.read(upToCount: 4096) ?? Data()
            fileName = url.lastPathComponent
            guard data.count >= 64, data[0] == 0x4D, data[1] == 0x5A else {
                isPE = false
                report = "Assinatura MZ ausente. O arquivo não foi reconhecido como executável PE."
                return
            }
            let peOffset = Int(data[0x3C]) | (Int(data[0x3D]) << 8) | (Int(data[0x3E]) << 16) | (Int(data[0x3F]) << 24)
            guard peOffset >= 0, peOffset + 6 <= data.count,
                  data[peOffset] == 0x50, data[peOffset + 1] == 0x45,
                  data[peOffset + 2] == 0, data[peOffset + 3] == 0 else {
                isPE = false
                report = "Cabeçalho PE inválido ou incompleto."
                return
            }
            let machine = UInt16(data[peOffset + 4]) | (UInt16(data[peOffset + 5]) << 8)
            let architecture: String
            switch machine {
            case 0x8664: architecture = "x86-64 (AMD64)"
            case 0x14c: architecture = "x86 (32 bits)"
            case 0xAA64: architecture = "ARM64"
            default: architecture = String(format: "desconhecida (0x%04X)", machine)
            }
            isPE = true
            report = "Cabeçalho PE válido. Arquitetura: \(architecture). Tamanho: \(ByteCountFormatter.string(fromByteCount: Int64((try? FileManager.default.attributesOfItem(atPath: url.path)[.size] as? NSNumber)?.int64Value ?? 0), countStyle: .file))."
        } catch {
            isPE = false
            report = "Falha ao abrir o arquivo: \(error.localizedDescription)"
        }
    }
}
