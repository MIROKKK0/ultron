import SwiftUI

struct ContentView: View {
    @AppStorage("ultronServerURL") private var serverURL = "https://ultron-api-c5ae.onrender.com"
    @State private var messages: [ChatMessage] = [
        ChatMessage(role: .assistant, text: "Olá. Eu sou o ULTRON. Estou pronta. Não precisa configurar token. Comandos: /self, /plan seu objetivo, /research sua pergunta e /calc 12*(3+4). A memória privada será ativada após autenticação segura por instalação.")
    ]
    @State private var draft = ""
    @State private var isSending = false
    @State private var showSettings = false
    @State private var errorMessage: String?
    @StateObject private var localModel = LocalModelManager()

    private let client = ChatClient()

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                HStack(spacing: 12) {
                    ZStack {
                        Circle().fill(Color.cyan.opacity(0.15))
                        Image(systemName: "sparkles").font(.system(size: 22, weight: .semibold)).foregroundStyle(.cyan)
                    }
                    .frame(width: 46, height: 46)
                    VStack(alignment: .leading, spacing: 3) {
                        Text("ULTRON").font(.headline.weight(.bold)).tracking(1.5)
                        Text(isSending ? "Respondendo…" : (localModel.isModelAvailable ? "FlyBrain + IA local" : "FlyBrain • IA local não instalada")).font(.caption).foregroundStyle(.secondary)
                    }
                    Spacer()
                    Circle().fill(serverURL.isEmpty ? .orange : .green).frame(width: 8, height: 8)
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
                                        serverURL: serverURL,
                                    )
                                }
                                .id(message.id)
                            }
                            if isSending {
                                HStack {
                                    ProgressView().tint(.cyan)
                                    Text("ULTRON está respondendo").font(.caption).foregroundStyle(.secondary)
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
                SettingsView(serverURL: $serverURL, localModel: localModel)
                    .presentationDetents([.medium, .large])
            }
        }
        .preferredColorScheme(.dark)
        .task(id: serverURL) {
            // Render Free can sleep while idle; warm it in the background at launch.
            await client.warmUp(serverURL: serverURL)
        }
    }

    private static func requiresExactServerReply(_ text: String) -> Bool {
        let normalized = text.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return normalized.hasPrefix("/calc ") || normalized == "/self" ||
            normalized.hasPrefix("/remember ")
    }

    private func send() {
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !isSending else { return }
        draft = ""
        errorMessage = nil
        messages.append(ChatMessage(role: .user, text: text))
        isSending = true

        Task {
            do {
                let result = try await client.send(text, serverURL: serverURL)
                // Show the server/FlyBrain answer immediately while the local model
                // improves its wording in a visible token stream.
                let assistantMessage = ChatMessage(role: .assistant, text: result.reply, strategy: result.strategy)
                messages.append(assistantMessage)

                if localModel.isModelAvailable && !Self.requiresExactServerReply(text) {
                    do {
                        let stream = try await localModel.stream(
                            userMessage: text,
                            previousMessages: Array(messages.dropLast(2).suffix(4)),
                            brainContext: result.brainContext,
                            serverReply: result.reply
                        )
                        var generated = ""
                        for try await token in stream {
                            generated += token
                            if let index = messages.firstIndex(where: { $0.id == assistantMessage.id }) {
                                messages[index].text = generated
                            }
                        }
                        let cleaned = generated
                            .replacingOccurrences(of: "<think>[\\s\\S]*?</think>", with: "", options: .regularExpression)
                            .trimmingCharacters(in: .whitespacesAndNewlines)
                        if let index = messages.firstIndex(where: { $0.id == assistantMessage.id }) {
                            messages[index].text = cleaned.isEmpty ? result.reply : cleaned
                        }
                    } catch {
                        if let index = messages.firstIndex(where: { $0.id == assistantMessage.id }) {
                            messages[index].text = result.reply
                        }
                        errorMessage = "Mantive a resposta do FlyBrain; a geração local falhou: \(error.localizedDescription)"
                    }
                }
            } catch {
                errorMessage = error.localizedDescription
                messages.append(ChatMessage(role: .assistant, text: "Não consegui concluir a solicitação. Confira o servidor e a conexão."))
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
    @ObservedObject var localModel: LocalModelManager
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
                Section("Cérebro linguístico local") {
                    Text(localModel.isModelAvailable
                         ? "Qwen3 0.6B Q4_K_M está salvo neste iPhone. O FlyBrain processa primeiro; a geração local chega em fluxo, token por token."
                         : "Baixe o modelo Qwen3 0.6B quantizado (~462 MiB). A inferência acontece no iPhone via llama.cpp/Metal; não usa chave de IA.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    if localModel.isDownloading {
                        ProgressView("Baixando modelo (~462 MiB)…")
                    } else if localModel.isModelAvailable {
                        Label("Modelo disponível", systemImage: "checkmark.circle.fill")
                            .foregroundStyle(.green)
                        Button("Remover modelo deste iPhone", role: .destructive) {
                            Task { await localModel.removeModel() }
                        }
                    } else {
                        Button("Baixar modelo local (~462 MiB)") {
                            Task { await localModel.downloadModel() }
                        }
                        .disabled(localModel.isDownloading)
                    }
                    if let modelError = localModel.errorMessage {
                        Text(modelError).font(.caption).foregroundStyle(.red)
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
