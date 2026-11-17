import SwiftUI

struct ContentView: View {
    @AppStorage("ultronServerURL") private var serverURL = "https://ultron-api-c5ae.onrender.com"
    @State private var messages: [ChatMessage] = [
        ChatMessage(role: .assistant, text: "Olá. Sou o ULTRON. Use /plan, /research, /calc, /self e /skills. Memória privada: /remember texto, /memories ou /forget ID. A geração livre ainda está em desenvolvimento.")
    ]
    @State private var draft = ""
    @State private var isSending = false
    @State private var brainPhase: BrainPhase = .idle
    @State private var showSettings = false
    @State private var errorMessage: String?
    @State private var serverOnline = false
    @State private var serverStatusChecked = false

    private let client = ChatClient()

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                HStack(spacing: 12) {
                    BrainMonitorView(phase: brainPhase)
                    VStack(alignment: .leading, spacing: 3) {
                        Text("ULTRON").font(.headline.weight(.bold)).tracking(1.5)
                        Text(isSending ? brainPhase.title : (serverOnline ? "API conectada" : (serverStatusChecked ? "API indisponível" : "Verificando API"))).font(.caption).foregroundStyle(.secondary)
                    }
                    Spacer()
                    Circle()
                        .fill(serverOnline ? .green : (serverStatusChecked ? .red : .orange))
                        .frame(width: 8, height: 8)
                        .accessibilityLabel(serverOnline ? "API online" : (serverStatusChecked ? "API offline" : "Verificando API"))
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
                SettingsView(serverURL: $serverURL)
                    .presentationDetents([.medium, .large])
            }
        }
        .preferredColorScheme(.dark)
        .task { await refreshServerStatus() }
        .onChange(of: serverURL) { _ in
            serverStatusChecked = false
            Task { await refreshServerStatus() }
        }
    }

    private func refreshServerStatus() async {
        serverOnline = await client.checkHealth(serverURL: serverURL)
        serverStatusChecked = true
    }

    private func send() {
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !isSending else { return }
        draft = ""
        errorMessage = nil
        messages.append(ChatMessage(role: .user, text: text))
        isSending = true
        brainPhase = .connecting

        Task {
            do {
                if text.lowercased().hasPrefix("/remember ") {
                    let content = String(text.dropFirst("/remember ".count)).trimmingCharacters(in: .whitespacesAndNewlines)
                    guard !content.isEmpty else { throw ChatClientError.invalidResponse }
                    let id = try await client.remember(content, serverURL: serverURL)
                    serverOnline = true
                    serverStatusChecked = true
                    brainPhase = .responding
                    messages.append(ChatMessage(role: .assistant, text: "Memória privada salva com sucesso. ID: \(id)"))
                    isSending = false
                    return
                }
                if text.lowercased() == "/memories" {
                    let items = try await client.listMemories(serverURL: serverURL)
                    serverOnline = true
                    serverStatusChecked = true
                    brainPhase = .responding
                    let output = items.isEmpty ? "Ainda não há memórias privadas salvas." : "Suas memórias privadas:\n" + items.joined(separator: "\n")
                    messages.append(ChatMessage(role: .assistant, text: output))
                    isSending = false
                    return
                }
                if text.lowercased().hasPrefix("/forget ") {
                    let rawID = String(text.dropFirst("/forget ".count)).trimmingCharacters(in: .whitespacesAndNewlines)
                    guard let id = Int(rawID), id > 0 else {
                        messages.append(ChatMessage(role: .assistant, text: "Use /forget seguido do ID numérico da memória."))
                        isSending = false
                        return
                    }
                    try await client.forgetMemory(id, serverURL: serverURL)
                    serverOnline = true
                    serverStatusChecked = true
                    brainPhase = .responding
                    messages.append(ChatMessage(role: .assistant, text: "Memória \(id) apagada."))
                    isSending = false
                    return
                }
                let result = try await client.send(text, serverURL: serverURL) { phase in
                    brainPhase = phase
                }
                serverOnline = true
                serverStatusChecked = true
                brainPhase = .responding
                messages.append(ChatMessage(role: .assistant, text: result.reply, strategy: result.strategy))
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
                        Text("Estratégia local: \(strategy)")
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
    @Environment(\.dismiss) private var dismiss
    @State private var draftURL = ""

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
                Section {
                    Button("Salvar configuração") {
                        serverURL = draftURL.trimmingCharacters(in: .whitespacesAndNewlines)
                        dismiss()
                    }
                    .disabled(!draftURL.lowercased().hasPrefix("https://"))
                }
            }
            .navigationTitle("Configurações")
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
