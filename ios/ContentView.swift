import SwiftUI

struct ContentView: View {
    @AppStorage("ultronServerURL") private var serverURL = "https://ultron-api-c5ae.onrender.com"
    @AppStorage("ultronChatHistoryData") private var storedChatHistory: Data = Data()
    @State private var messages: [ChatMessage] = [
        ChatMessage(role: .assistant, text: "Olá. Sou o ULTRON. Converse normalmente: peça para planejar, pesquisar, calcular, aprender programação ou consultar sua memória. Sua memória fica isolada nesta instalação.")
    ]
    @State private var draft = ""
    @State private var isSending = false
    @State private var brainPhase: BrainPhase = .idle
    @State private var showSettings = false
    @State private var showMemoryExplorer = false
    @State private var errorMessage: String?
    @State private var serverOnline = false
    @State private var serverStatusChecked = false

    private let client = ChatClient()

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                HStack(spacing: 12) {
                    NeuralActivityView(phase: brainPhase)
                    VStack(alignment: .leading, spacing: 3) {
                        Text("ULTRON").font(.headline.weight(.bold)).tracking(1.5)
                        Text(isSending ? brainPhase.title : (serverOnline ? "API conectada" : (serverStatusChecked ? "API indisponível" : "Verificando API"))).font(.caption).foregroundStyle(.secondary)
                    }
                    Spacer()
                    Circle()
                        .fill(serverOnline ? .green : (serverStatusChecked ? .red : .orange))
                        .frame(width: 8, height: 8)
                        .accessibilityLabel(serverOnline ? "API online" : (serverStatusChecked ? "API offline" : "Verificando API"))
                    Button { showMemoryExplorer = true } label: {
                        Image(systemName: "circle.hexagongrid").font(.title3).padding(10)
                    }
                    .accessibilityLabel("Explorar memória neural")
                    Button { showSettings = true } label: {
                        Image(systemName: "slider.horizontal.3").font(.title3).padding(10)
                    }
                    .accessibilityLabel("Configurações")
                }
                .padding()

                Divider()

                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 14) {
                            ForEach(messages) { message in
                                MessageBubble(message: message) { rating, strategy in
                                    try await client.sendFeedback(
                                        rating,
                                        strategy: strategy,
                                        serverURL: serverURL
                                    )
                                }
                                .id(message.id)
                            }
                            if isSending {
                                HStack {
                                    ProgressView().tint(.cyan)
                                    Text("ULTRON está pensando").font(.caption).foregroundStyle(.secondary)
                                    Spacer()
                                }
                                .padding(.horizontal)
                            }
                        }
                        .padding(.vertical, 18)
                    }
                    .onChange(of: messages.count) { _ in
                        if let last = messages.last { proxy.scrollTo(last.id, anchor: .bottom) }
                    }
                }

                if let errorMessage {
                    Text(errorMessage)
                        .font(.caption)
                        .foregroundStyle(.red)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.horizontal)
                        .padding(.bottom, 6)
                }

                HStack(alignment: .bottom, spacing: 10) {
                    TextField("Fale com o ULTRON…", text: $draft, axis: .vertical)
                        .lineLimit(1...5)
                        .padding(12)
                        .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 18))
                    Button(action: send) {
                        Image(systemName: "arrow.up")
                            .font(.headline.weight(.bold))
                            .foregroundStyle(.black)
                            .frame(width: 44, height: 44)
                            .background(Color.cyan, in: Circle())
                    }
                    .disabled(draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isSending)
                    .opacity(draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isSending ? 0.45 : 1)
                    .accessibilityLabel("Enviar mensagem")
                }
                .padding()
            }
            .background(Color(.systemBackground))
            .navigationBarHidden(true)
            .sheet(isPresented: $showSettings) {
                SettingsView(serverURL: $serverURL, onClearHistory: clearLocalHistory)
                    .presentationDetents([.medium, .large])
            }
            .sheet(isPresented: $showMemoryExplorer) {
                NavigationStack {
                    MemoryExplorerView(serverURL: serverURL)
                }
                .preferredColorScheme(.dark)
            }
        }
        .preferredColorScheme(.dark)
        .task {
            restoreLocalHistory()
            await refreshServerStatus()
        }
        .onChange(of: messages) { _ in persistLocalHistory() }
        .onChange(of: serverURL) { _ in
            serverStatusChecked = false
            Task { await refreshServerStatus() }
        }
    }

    private func restoreLocalHistory() {
        guard !storedChatHistory.isEmpty,
              let decoded = try? JSONDecoder().decode([ChatMessage].self, from: storedChatHistory),
              !decoded.isEmpty else { return }
        messages = Array(decoded.suffix(60))
    }

    private func persistLocalHistory() {
        let bounded = messages.suffix(60).map {
            ChatMessage(role: $0.role, text: String($0.text.prefix(4000)), strategy: $0.strategy)
        }
        if let encoded = try? JSONEncoder().encode(bounded) {
            storedChatHistory = encoded
        }
    }

    private func clearLocalHistory() {
        storedChatHistory = Data()
        messages = [
            ChatMessage(role: .assistant, text: "Histórico apagado. Olá! Sou o ULTRON. Como posso ajudar?")
        ]
    }

    private func refreshServerStatus() async {
        serverOnline = await client.checkHealth(serverURL: serverURL)
        serverStatusChecked = true
    }

    private func handleMemoryCommand(_ text: String) async throws -> String? {
        let command = text.trimmingCharacters(in: .whitespacesAndNewlines)
        let lowered = command.lowercased()

        if lowered.hasPrefix("/remember ") {
            let payload = String(command.dropFirst("/remember ".count)).trimmingCharacters(in: .whitespacesAndNewlines)
            guard !payload.isEmpty else { return "Use /remember texto para salvar uma memória semântica." }
            let parts = payload.split(separator: " ", maxSplits: 1).map(String.init)
            let allowedKinds = ["episodic", "semantic", "procedural"]
            let kind = parts.count == 2 && allowedKinds.contains(parts[0].lowercased()) ? parts[0].lowercased() : "semantic"
            let content = parts.count == 2 && allowedKinds.contains(parts[0].lowercased()) ? parts[1] : payload
            let outcome = try await client.rememberWithOfflineQueue(content, kind: kind, serverURL: serverURL)
            switch outcome {
            case .synced(let id):
                return "Memória privada salva (\(kind)). ID: \(id)"
            case .queued(let localID):
                return "Sem conexão com o servidor. Memória criptografada na fila offline. ID local: \(localID.uuidString)"
            }
        }

        if lowered == "/sync" {
            let report = try await client.syncQueuedMemories(serverURL: serverURL)
            return "Sincronização concluída. Enviadas: \(report.uploaded). Pendentes: \(report.remaining)."
        }

        if lowered == "/import-history" {
            let formatter = ISO8601DateFormatter()
            let records = messages.suffix(500).map { item in
                HistoryExportRecord(
                    role: item.role.rawValue,
                    content: item.text,
                    timestamp: formatter.string(from: item.createdAt ?? Date())
                )
            }
            guard !records.isEmpty else { return "Não há mensagens para importar." }
            let result = try await client.importHistory(
                sourceExport: "ios-local-chat-history-v1",
                records: records,
                serverURL: serverURL
            )
            return "Histórico importado. Novas memórias: \(result.imported). Duplicadas ignoradas: \(result.duplicates)."
        }

        if lowered == "/memories" {
            let items = try await client.listMemories(serverURL: serverURL)
            return items.isEmpty ? "Ainda não há memórias privadas salvas." : "Memórias desta instalação:\n" + items.joined(separator: "\n")
        }

        if lowered.hasPrefix("/forget ") {
            let rawID = String(command.dropFirst("/forget ".count)).trimmingCharacters(in: .whitespacesAndNewlines)
            guard let id = Int(rawID) else { return "Informe um ID válido: /forget 123." }
            try await client.forgetMemory(id, serverURL: serverURL)
            return "Memória \(id) apagada."
        }
        return nil
    }

    private func send() {
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !isSending else { return }
        draft = ""
        errorMessage = nil
        messages.append(ChatMessage(role: .user, text: text))
        let recentHistory = messages.suffix(9).dropLast().map { "\($0.role.rawValue): \($0.text)" }
        isSending = true
        brainPhase = .connecting

        Task {
            do {
                if let memoryReply = try await handleMemoryCommand(text) {
                    serverOnline = true
                    serverStatusChecked = true
                    brainPhase = .responding
                    messages.append(ChatMessage(role: .assistant, text: memoryReply))
                } else {
                    let result = try await client.send(text, serverURL: serverURL, history: recentHistory) { phase in
                        brainPhase = phase
                    }
                    serverOnline = true
                    serverStatusChecked = true
                    brainPhase = .responding
                    messages.append(ChatMessage(role: .assistant, text: result.reply, strategy: result.strategy))
                }
            } catch {
                serverOnline = false
                serverStatusChecked = true
                brainPhase = .error
                errorMessage = error.localizedDescription
                messages.append(ChatMessage(role: .assistant, text: "Não consegui concluir a solicitação. Confira o servidor e a conexão."))
            }
            if brainPhase == .responding {
                try? await Task.sleep(nanoseconds: 800_000_000)
                if brainPhase == .responding { brainPhase = .idle }
            }
            isSending = false
        }
    }
}

private struct MessageBubble: View {
    let message: ChatMessage
    let onFeedback: (Int, String) async throws -> Void
    @State private var feedbackSent = false
    @State private var feedbackError: String?

    var body: some View {
        HStack {
            if message.role == .user { Spacer(minLength: 48) }
            VStack(alignment: .leading, spacing: 8) {
                Text(message.text)
                    .font(.body)
                    .padding(.horizontal, 15)
                    .padding(.vertical, 12)
                    .foregroundStyle(message.role == .user ? .black : .primary)
                    .background(
                        message.role == .user ? Color.cyan : Color(.secondarySystemBackground),
                        in: RoundedRectangle(cornerRadius: 19)
                    )
                if message.role == .assistant {
                    HStack(spacing: 14) {
                        Button { DeviceActions.copy(message.text) } label: {
                            Label("Copiar", systemImage: "doc.on.doc")
                        }
                        Button { DeviceActions.speak(message.text) } label: {
                            Label("Ouvir", systemImage: "speaker.wave.2")
                        }
                        Button { DeviceActions.stopSpeaking() } label: {
                            Image(systemName: "stop.fill")
                        }
                        ShareLink(item: message.text) {
                            Label("Compartilhar", systemImage: "square.and.arrow.up")
                        }
                        if let url = DeviceActions.firstHTTPSURL(in: message.text) {
                            Link(destination: url) {
                                Label("Abrir link", systemImage: "safari")
                            }
                        }
                    }
                    .font(.caption)
                    .buttonStyle(.borderless)
                    .foregroundStyle(.cyan)
                    .padding(.horizontal, 8)
                }
                if message.role == .assistant, let strategy = message.strategy {
                    HStack(spacing: 12) {
                        Text("Estratégia neural: \(strategy)")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                        Spacer()
                        if feedbackSent {
                            Text("Feedback registrado")
                                .font(.caption2)
                                .foregroundStyle(.green)
                        } else {
                            Button {
                                Task {
                                    do {
                                        try await onFeedback(5, strategy)
                                        feedbackSent = true
                                        feedbackError = nil
                                    } catch {
                                        feedbackError = error.localizedDescription
                                    }
                                }
                            } label: {
                                Image(systemName: "hand.thumbsup")
                            }
                            .accessibilityLabel("Resposta útil")
                            Button {
                                Task {
                                    do {
                                        try await onFeedback(1, strategy)
                                        feedbackSent = true
                                        feedbackError = nil
                                    } catch {
                                        feedbackError = error.localizedDescription
                                    }
                                }
                            } label: {
                                Image(systemName: "hand.thumbsdown")
                            }
                            .accessibilityLabel("Resposta não útil")
                        }
                    }
                    .padding(.horizontal, 8)
                    if let feedbackError {
                        Text("Falha no feedback: \\(feedbackError)")
                            .font(.caption2)
                            .foregroundStyle(.red)
                            .padding(.horizontal, 8)
                    }
                }
            }
            if message.role == .assistant { Spacer(minLength: 48) }
        }
        .padding(.horizontal)
        .frame(maxWidth: .infinity)
    }
}

private struct SettingsView: View {
    @Binding var serverURL: String
    let onClearHistory: () -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var draftURL = ""
    @State private var confirmClearHistory = false

    var body: some View {
        NavigationStack {
            Form {
                Section("Servidor do ULTRON") {
                    TextField("https://ultron-api.example.onrender.com", text: $draftURL)
                        .keyboardType(.URL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    Text("Use o endereço HTTPS do servidor. O chat público usa limite de requisições e não pede token manual.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Section("Privacidade neste iPhone") {
                    Text("As últimas 60 mensagens ficam salvas localmente neste aparelho para manter contexto entre aberturas. O histórico não é enviado inteiro ao servidor; somente até 8 mensagens recentes acompanham cada pergunta.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Button("Apagar histórico local", role: .destructive) {
                        confirmClearHistory = true
                    }
                }
                Section {
                    Button("Salvar configuração") {
                        serverURL = draftURL.trimmingCharacters(in: .whitespacesAndNewlines)
                        dismiss()
                    }
                    .disabled(!draftURL.lowercased().hasPrefix("https://"))
                }
            }
            .navigationTitle("Configurações")
            .confirmationDialog(
                "Apagar o histórico do ULTRON?",
                isPresented: $confirmClearHistory,
                titleVisibility: .visible
            ) {
                Button("Apagar histórico local", role: .destructive) {
                    onClearHistory()
                    dismiss()
                }
                Button("Cancelar", role: .cancel) {}
            } message: {
                Text("Isso apaga as mensagens salvas neste iPhone. Não apaga dados de outros serviços.")
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Fechar") { dismiss() }
                }
            }
            .onAppear {
                draftURL = serverURL
            }
        }
        .preferredColorScheme(.dark)
    }
}
