import SwiftUI
import UniformTypeIdentifiers

private struct REAToolsResponse: Decodable {
    let tools: [REATool]
}

private struct REATool: Decodable, Identifiable {
    let name: String
    let description: String?
    var id: String { name }
}

struct ReverseEngineeringView: View {
    let serverURL: String
    let client: ChatClient

    @Environment(\.dismiss) private var dismiss
    @State private var mode = "SITE"
    @State private var targetURL = ""
    @State private var selectedIPA: URL?
    @State private var showImporter = false
    @State private var tools: [REATool] = []
    @State private var selectedTool = ""
    @State private var filter = ""
    @State private var arguments = "{}"
    @State private var uploadedFilePath = ""
    @State private var output = "Conecte ao motor REA para carregar as ferramentas de análise."
    @State private var busy = false

    private var filteredTools: [REATool] {
        let terms = mode == "SITE"
            ? ["web", "browser", "website", "javascript", "http", "page", "capture", "inspect"]
            : ["apple", "application", "binary", "package", "artifact", "ipa", "plist", "inspect"]
        let matching = tools.filter { tool in
            let text = (tool.name + " " + (tool.description ?? "")).lowercased()
            return terms.contains(where: text.contains)
        }
        return (matching.isEmpty ? tools : matching).sorted { $0.name < $1.name }
    }

    private var selectedDescription: String {
        tools.first(where: { $0.name == selectedTool })?.description ?? ""
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Tipo de análise") {
                    Picker("Alvo", selection: $mode) {
                        Text("Site").tag("SITE")
                        Text("IPA").tag("IPA")
                    }
                    .pickerStyle(.segmented)
                    if mode == "SITE" {
                        TextField("https://dominio-autorizado.com", text: $targetURL)
                            .keyboardType(.URL)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                    } else {
                        Button {
                            showImporter = true
                        } label: {
                            Label(selectedIPA?.lastPathComponent ?? "Selecionar arquivo IPA", systemImage: "doc.zipper")
                        }
                        if let selectedIPA {
                            Text("Selecionado: \(selectedIPA.lastPathComponent)")
                                .font(.caption)
                                .foregroundStyle(.green)
                                .textSelection(.enabled)
                        }
                        Button("Enviar IPA ao REA", systemImage: "arrow.up.doc", action: uploadIPA)
                            .disabled(busy || selectedIPA == nil)
                        if !uploadedFilePath.isEmpty {
                            Text("Arquivo recebido pelo bridge. Caminho disponível para a ferramenta REA.")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                Section("Motor REA") {
                    Button("Conectar e descobrir ferramentas", systemImage: "antenna.radiowaves.left.and.right", action: discoverTools)
                        .disabled(busy)
                    Text("\(tools.count) ferramentas MCP descobertas")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    if !tools.isEmpty {
                        TextField("Filtrar ferramentas", text: $filter)
                            .textInputAutocapitalization(.never)
                        Picker("Ferramenta", selection: $selectedTool) {
                            ForEach(filteredTools) { tool in
                                Text(tool.name).tag(tool.name)
                            }
                        }
                        .onChange(of: selectedTool) { _ in prefillArguments() }
                        if !selectedDescription.isEmpty {
                            Text(selectedDescription)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                if !selectedTool.isEmpty {
                    Section("Argumentos da ferramenta") {
                        Text("Confira o schema antes de executar. Para IPA, use o caminho retornado pelo upload no campo de arquivo.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        TextEditor(text: $arguments)
                            .font(.system(.footnote, design: .monospaced))
                            .frame(minHeight: 140)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                        Button("Executar ferramenta REA", systemImage: "play.fill", action: callTool)
                            .disabled(busy)
                    }
                }

                Section("Resultado e evidências") {
                    if busy { ProgressView("ULTRON está trabalhando com REA…") }
                    Text(output)
                        .font(.system(.footnote, design: .monospaced))
                        .textSelection(.enabled)
                }

                Section {
                    Text("Use somente sites, aplicativos e arquivos que você possui ou tem autorização para analisar. A análise não garante reconstrução idêntica; código, APIs privadas, servidores e recursos protegidos podem não estar disponíveis.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Engenharia reversa")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Fechar") { dismiss() }
                }
            }
            .fileImporter(
                isPresented: $showImporter,
                allowedContentTypes: [.data],
                allowsMultipleSelection: false
            ) { result in
                switch result {
                case .success(let urls):
                    guard let url = urls.first, url.pathExtension.lowercased() == "ipa" else {
                        output = "Selecione um arquivo com extensão .ipa."
                        selectedIPA = nil
                        return
                    }
                    selectedIPA = url
                    uploadedFilePath = ""
                    output = "IPA selecionado: \(url.lastPathComponent). Toque em Enviar IPA ao REA."
                case .failure(let error):
                    output = "Não foi possível selecionar o arquivo: \(error.localizedDescription)"
                }
            }
        }
        .preferredColorScheme(.dark)
    }

    private func discoverTools() {
        busy = true
        Task {
            defer { busy = false }
            do {
                let data = try await client.reaTools(serverURL: serverURL)
                let response = try JSONDecoder().decode(REAToolsResponse.self, from: data)
                tools = response.tools
                selectedTool = filteredTools.first?.name ?? response.tools.first?.name ?? ""
                output = "Conexão com REA concluída. \(response.tools.count) ferramentas MCP disponíveis."
                prefillArguments()
            } catch {
                output = "Falha ao conectar ao REA: \(error.localizedDescription)"
            }
        }
    }

    private func uploadIPA() {
        guard let selectedIPA else { return }
        busy = true
        output = "Enviando o IPA com transferência em blocos…"
        Task {
            defer { busy = false }
            do {
                let data = try await client.uploadREAIPA(fileURL: selectedIPA, serverURL: serverURL)
                let result = try JSONSerialization.jsonObject(with: data) as? [String: Any]
                uploadedFilePath = result?["filePath"] as? String ?? ""
                output = String(data: data, encoding: .utf8) ?? "Upload concluído, resposta não textual."
                prefillArguments()
            } catch {
                output = "Falha no upload: \(error.localizedDescription)"
            }
        }
    }

    private func prefillArguments() {
        guard let tool = tools.first(where: { $0.name == selectedTool }),
              let data = try? JSONSerialization.data(withJSONObject: ["tools": [["name": tool.name]]]),
              let catalog = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let _ = catalog["tools"] else { return }
        // The MCP schema is rendered by the server; start with safe, editable JSON.
        // The target is never guessed into an unknown required field.
        if mode == "SITE", let url = URL(string: targetURL), url.scheme == "https" {
            arguments = (try? String(data: JSONSerialization.data(
                withJSONObject: ["url": url.absoluteString],
                options: [.prettyPrinted, .sortedKeys]
            ), encoding: .utf8)) ?? "{}"
        } else if mode == "IPA", !uploadedFilePath.isEmpty {
            arguments = (try? String(data: JSONSerialization.data(
                withJSONObject: ["filePath": uploadedFilePath],
                options: [.prettyPrinted, .sortedKeys]
            ), encoding: .utf8)) ?? "{}"
        } else {
            arguments = "{}"
        }
    }

    private func callTool() {
        guard let data = arguments.data(using: .utf8),
              (try? JSONSerialization.jsonObject(with: data) as? [String: Any]) != nil else {
            output = "Os argumentos precisam ser um objeto JSON válido."
            return
        }
        busy = true
        Task {
            defer { busy = false }
            do {
                let result = try await client.callREATool(selectedTool, arguments: data, serverURL: serverURL)
                output = String(data: result, encoding: .utf8) ?? "O REA retornou uma resposta não textual."
            } catch {
                output = "A execução REA falhou: \(error.localizedDescription)"
            }
        }
    }
}
