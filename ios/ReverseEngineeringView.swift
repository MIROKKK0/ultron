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
    @State private var siteAuthorized = false
    @State private var selectedIPA: URL?
    @State private var showImporter = false
    @State private var tools: [REATool] = []
    @State private var catalogData: Data?
    @State private var selectedTool = ""
    @State private var filter = ""
    @State private var arguments = "{}"
    @State private var uploadedFilePath = ""
    @State private var uploadedFileID = ""
    @State private var analysisRunURL = ""
    @State private var output = "Conecte ao motor REA para carregar as ferramentas de análise."
    @State private var busy = false

    private var filteredTools: [REATool] {
        let safeExact = ["open_binary", "capture_web_screenshot", "observe_web_session", "export_evidence_bundle"]
        let safePrefixes = ["analyze_", "inspect_", "list_", "compare_", "read_", "decode_", "disassemble_", "export_", "get_", "find_", "search_"]
        let safe = tools.filter { tool in
            safeExact.contains(tool.name) || safePrefixes.contains(where: tool.name.hasPrefix)
        }
        let terms = mode == "SITE"
            ? ["web", "browser", "website", "javascript", "http", "page", "inspect"]
            : ["apple", "application", "binary", "package", "artifact", "ipa", "plist", "inspect"]
        let matching = safe.filter { tool in
            let text = (tool.name + " " + (tool.description ?? "")).lowercased()
            return terms.contains(where: text.contains)
        }
        let candidates = (matching.isEmpty ? safe : matching).sorted { $0.name < $1.name }
        guard !filter.isEmpty else { return candidates }
        return candidates.filter { ($0.name + " " + ($0.description ?? "")).localizedCaseInsensitiveContains(filter) }
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
                    .onChange(of: mode) { _ in
                        selectedTool = filteredTools.first?.name ?? ""
                        prefillArguments()
                    }
                    if mode == "SITE" {
                        Text("ULTRON inicia um Chromium descartável e isolado; o REA observa a página por CDP, captura scripts e gera evidências. Só HTTPS público; redirecionamentos para outra origem são interrompidos.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    if mode == "SITE" {
                        TextField("https://dominio-autorizado.com", text: $targetURL)
                            .keyboardType(.URL)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                        Button("Analisar site com Chromium + REA", systemImage: "globe", action: analyzeSite)
                            .disabled(busy || !siteAuthorized || URL(string: targetURL)?.scheme != "https")
                        Toggle("Tenho autorização para analisar este site", isOn: $siteAuthorized)
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
                        Button("Analisar IPA com REA + Ghidra", systemImage: "cpu", action: analyzeIPA)
                            .disabled(busy || uploadedFileID.isEmpty)
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
                        Text("Confira os campos exigidos pela ferramenta. Para IPA, o caminho retornado pelo upload é inserido automaticamente quando o schema reconhece um campo de arquivo.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Text(selectedSchemaText)
                            .font(.system(.caption2, design: .monospaced))
                            .foregroundStyle(.secondary)
                            .textSelection(.enabled)
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
                    if let url = URL(string: analysisRunURL), url.scheme == "https" {
                        Link("Abrir execução e baixar evidências completas", destination: url)
                    }
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
                    uploadedFileID = ""
                    analysisRunURL = ""
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
                catalogData = data
                tools = response.tools
                selectedTool = filteredTools.first?.name ?? ""
                output = "Conexão com REA concluída. \(response.tools.count) ferramentas MCP disponíveis."
                prefillArguments()
            } catch {
                output = "Falha ao conectar ao REA: \(error.localizedDescription)"
            }
        }
    }

    private func startSiteAnalysis() {
        guard siteAuthorized else { return }
        busy = true
        output = "ULTRON está enviando o site para um worker isolado do REA…"
        Task {
            defer { busy = false }
            do {
                let data = try await client.startREASiteAnalysis(
                    url: targetURL,
                    authorized: siteAuthorized,
                    serverURL: serverURL
                )
                let result = try JSONSerialization.jsonObject(with: data) as? [String: Any]
                siteAnalysisID = result?["analysis_id"] as? String ?? ""
                siteRunURL = result?["run_url"] as? String ?? ""
                siteStatus = result?["status"] as? String ?? "dispatched"
                output = "Análise de site enviada ao worker temporário. O REA vai abrir o site num Chromium isolado, recolher evidências e analisar os scripts observados. Abra a execução para acompanhar e descarregar o relatório."
            } catch {
                output = "Não foi possível iniciar a análise do site: \(error.localizedDescription)"
            }
        }
    }

    private func refreshSiteStatus() {
        guard !siteAnalysisID.isEmpty else { return }
        busy = true
        Task {
            defer { busy = false }
            do {
                let data = try await client.reaSiteAnalysisStatus(id: siteAnalysisID, serverURL: serverURL)
                let result = try JSONSerialization.jsonObject(with: data) as? [String: Any]
                siteStatus = result?["conclusion"] as? String ?? result?["status"] as? String ?? "unknown"
                siteRunURL = result?["run_url"] as? String ?? siteRunURL
                output = "Status da análise REA: \(siteStatus). O artefato fica disponível na execução do GitHub Actions quando o job terminar."
            } catch {
                output = "Falha ao consultar o status: \(error.localizedDescription)"
            }
        }
    }

    private func analyzeSite() {
        guard siteAuthorized,
              let url = URL(string: targetURL.trimmingCharacters(in: .whitespacesAndNewlines)),
              url.scheme == "https", url.host != nil else {
            output = "Informe uma URL HTTPS válida."
            return
        }
        runIsolatedAnalysis(targetType: "site", targetURL: url.absoluteString, fileID: nil)
    }

    private func analyzeIPA() {
        guard !uploadedFileID.isEmpty else {
            output = "Envie o IPA ao REA antes de iniciar a análise Ghidra."
            return
        }
        runIsolatedAnalysis(targetType: "ipa", targetURL: nil, fileID: uploadedFileID)
    }

    private func runIsolatedAnalysis(targetType: String, targetURL: String?, fileID: String?) {
        busy = true
        analysisRunURL = ""
        output = targetType == "site"
            ? "ULTRON está iniciando Chromium descartável, CDP e inspeção REA…"
            : "ULTRON está iniciando o worker isolado, extraindo o IPA e preparando Ghidra…"
        Task {
            defer { busy = false }
            do {
                let started = try await client.startREAWorkerJob(
                    targetType: targetType,
                    targetURL: targetURL,
                    fileID: fileID,
                    authorized: targetType == "site",
                    serverURL: serverURL
                )
                guard let startObject = try JSONSerialization.jsonObject(with: started) as? [String: Any],
                      let jobID = startObject["job_id"] as? String else {
                    throw ChatClientError.invalidResponse
                }
                output = "Análise enfileirada. ID: \(jobID). O worker roda fora do Render para não estourar a memória do servidor."
                for _ in 0..<270 {
                    try await Task.sleep(nanoseconds: 10_000_000_000)
                    let data = try await client.reaWorkerJobStatus(id: jobID, serverURL: serverURL)
                    guard let object = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                          let status = object["status"] as? String else {
                        throw ChatClientError.invalidResponse
                    }
                    if status == "succeeded" || status == "failed" {
                        let result = object["result"] as? [String: Any] ?? [:]
                        let summary = result["summary"] as? String ?? ""
                        analysisRunURL = result["run_url"] as? String ?? ""
                        output = (status == "succeeded" ? "ANÁLISE CONCLUÍDA — ULTRON + REA" : "ANÁLISE COM FALHAS — VER LIMITAÇÕES") +
                            "\n\n" + String(summary.prefix(18000))
                        if !analysisRunURL.isEmpty { output += "\n\nEvidências completas: \(analysisRunURL)" }
                        if let error = object["error"] as? String, !error.isEmpty { output += "\n\nErro: \(error)" }
                        return
                    }
                    output = "Worker em execução (\(status)). O app continuará consultando o resultado. ID: \(jobID)"
                }
                output = "A análise ainda não terminou. ID: \(jobID). Você pode reabrir a execução do GitHub Actions quando o worker concluir."
            } catch {
                output = "Não foi possível iniciar ou consultar o worker: \(error.localizedDescription)"
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
                uploadedFileID = result?["id"] as? String ?? ""
                output = uploadedFileID.isEmpty
                    ? "O bridge não retornou um identificador seguro para o worker."
                    : "IPA recebido pelo REA. ID temporário: \(uploadedFileID). Agora você pode iniciar a análise Ghidra."
                prefillArguments()
            } catch {
                output = "Falha no upload: \(error.localizedDescription)"
            }
        }
    }

    private var selectedSchemaText: String {
        guard let catalogData,
              let root = try? JSONSerialization.jsonObject(with: catalogData) as? [String: Any],
              let items = root["tools"] as? [[String: Any]],
              let tool = items.first(where: { ($0["name"] as? String) == selectedTool }),
              let schema = tool["inputSchema"],
              let data = try? JSONSerialization.data(withJSONObject: schema, options: [.prettyPrinted, .sortedKeys]) else {
            return "Schema não informado pelo servidor REA."
        }
        return String(data: data, encoding: .utf8) ?? "Schema indisponível."
    }

    private func prefillArguments() {
        guard let catalogData,
              let root = try? JSONSerialization.jsonObject(with: catalogData) as? [String: Any],
              let items = root["tools"] as? [[String: Any]],
              let tool = items.first(where: { ($0["name"] as? String) == selectedTool }),
              let schema = tool["inputSchema"] as? [String: Any],
              let properties = schema["properties"] as? [String: [String: Any]] else {
            arguments = "{}"
            return
        }
        let required = Set(schema["required"] as? [String] ?? [])
        var values: [String: Any] = [:]
        for (key, property) in properties {
            let normalized = key.lowercased()
            let rawType = property["type"]
            let type = rawType as? String ?? (rawType as? [String])?.first ?? "string"
            if mode == "SITE", (normalized.contains("url") || normalized == "target") {
                if let url = URL(string: targetURL), url.scheme == "https" {
                    values[key] = url.absoluteString
                } else if required.contains(key) {
                    values[key] = ""
                }
            } else if mode == "IPA", !uploadedFilePath.isEmpty,
                      ["path", "file", "binary", "artifact", "package"].contains(where: normalized.contains) {
                values[key] = uploadedFilePath
            } else if required.contains(key) {
                switch type {
                case "string": values[key] = ""
                case "number", "integer": values[key] = 0
                case "boolean": values[key] = false
                case "array": values[key] = [Any]()
                case "object": values[key] = [String: Any]()
                default: break
                }
            }
        }
        guard let data = try? JSONSerialization.data(withJSONObject: values, options: [.prettyPrinted, .sortedKeys]) else {
            arguments = "{}"
            return
        }
        arguments = String(data: data, encoding: .utf8) ?? "{}"
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
