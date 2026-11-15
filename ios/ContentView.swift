import SwiftUI

struct ContentView: View {
    @AppStorage("ultronServerURL") private var serverURL = "https://ultron-api-c5ae.onrender.com"
    @State private var messages: [ChatMessage] = [
        ChatMessage(role: .assistant, text: "Olá! Sou o ULTRON. O FlyBrain coordena minhas respostas e posso pesquisar na web quando você pedir. Como posso ajudar?")
    ]
    @State private var draft = ""
    @State private var isSending = false
    @State private var showSettings = false
    @State private var errorMessage: String?
    @State private var failedMessage: String?
    @State private var serverOnline = false
    @State private var checkingServer = true
    @StateObject private var localModel = LocalModelManager()
    @FocusState private var composerFocused: Bool

    private let client = ChatClient()

    private var connectionLabel: String {
        if checkingServer { return "Conectando" }
        return serverOnline ? "Servidor online" : "Sem conexão"
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                header

                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 18) {
                            if messages.count == 1 {
                                suggestions
                                    .padding(.top, 18)
                            }

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
                                HStack(spacing: 10) {
                                    ProgressView().tint(.red)
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text("ULTRON está trabalhando")
                                            .font(.subheadline.weight(.medium))
                                        Text("FlyBrain está processando sua mensagem")
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
                                    }
                                    Spacer()
                                }
                                .padding(14)
                                .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 18))
                                .padding(.horizontal)
                                .id("typing")
                            }
                        }
                        .padding(.vertical, 20)
                    }
                    .scrollDismissesKeyboard(.interactively)
                    .onChange(of: messages.count) { _ in
                        if let last = messages.last {
                            withAnimation(.easeOut(duration: 0.2)) {
                                proxy.scrollTo(last.id, anchor: .bottom)
                            }
                        }
                    }
                    .onChange(of: isSending) { sending in
                        if sending {
                            withAnimation(.easeOut(duration: 0.2)) {
                                proxy.scrollTo("typing", anchor: .bottom)
                            }
                        }
                    }
                }

                if let errorMessage {
                    errorPanel(errorMessage)
                }

                composer
            }
            .background(Color(uiColor: .systemBackground))
            .toolbar(.hidden, for: .navigationBar)
            .sheet(isPresented: $showSettings) {
                SettingsView(serverURL: $serverURL, localModel: localModel)
                    .presentationDetents([.medium, .large])
            }
        }
        .preferredColorScheme(.dark)
        .task(id: serverURL) {
            checkingServer = true
            serverOnline = await client.warmUp(serverURL: serverURL)
            checkingServer = false
        }
    }

    private var header: some View {
        HStack(spacing: 12) {
            ZStack {
                Circle().fill(Color.red.opacity(0.14))
                Image(systemName: "brain.head.profile")
                    .font(.system(size: 23, weight: .semibold))
                    .foregroundStyle(.red)
            }
            .frame(width: 46, height: 46)

            VStack(alignment: .leading, spacing: 4) {
                Text("ULTRON")
                    .font(.system(size: 18, weight: .bold, design: .rounded))
                    .tracking(1.6)
                HStack(spacing: 6) {
                    Circle()
                        .fill(checkingServer ? Color.orange : (serverOnline ? Color.green : Color.red))
                        .frame(width: 7, height: 7)
                    Text(connectionLabel)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text("·")
                        .foregroundStyle(.tertiary)
                    Text(localModel.isModelAvailable ? "IA local pronta" : "FlyBrain")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Spacer(minLength: 8)

            Button {
                Task {
                    checkingServer = true
                    serverOnline = await client.warmUp(serverURL: serverURL)
                    checkingServer = false
                }
            } label: {
                Image(systemName: "arrow.clockwise")
                    .font(.system(size: 17, weight: .medium))
                    .frame(width: 40, height: 40)
                    .background(Color(.secondarySystemBackground), in: Circle())
            }
            .accessibilityLabel("Verificar conexão")

            Button { showSettings = true } label: {
                Image(systemName: "slider.horizontal.3")
                    .font(.system(size: 19, weight: .medium))
                    .frame(width: 40, height: 40)
                    .background(Color(.secondarySystemBackground), in: Circle())
            }
            .accessibilityLabel("Configurações")
        }
        .padding(.horizontal, 18)
        .padding(.vertical, 12)
        .background(.ultraThinMaterial)
        .overlay(alignment: .bottom) {
            Rectangle().fill(Color.white.opacity(0.07)).frame(height: 1)
        }
    }

    private var suggestions: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("O que vamos fazer?")
                .font(.headline)
            Text("Peça em linguagem natural. Não precisa decorar comandos.")
                .font(.caption)
                .foregroundStyle(.secondary)

            VStack(spacing: 9) {
                suggestion("Pesquise um vídeo do YouTube sobre inteligência artificial", icon: "play.rectangle")
                suggestion("Explique como funciona o FlyWire", icon: "brain")
                suggestion("Pesquise as notícias mais recentes de tecnologia", icon: "globe")
            }
        }
        .padding(16)
        .background(Color(.secondarySystemBackground).opacity(0.7), in: RoundedRectangle(cornerRadius: 22))
        .padding(.horizontal)
    }

    private func suggestion(_ title: String, icon: String) -> some View {
        Button {
            draft = title
            composerFocused = true
        } label: {
            HStack(spacing: 10) {
                Image(systemName: icon)
                    .foregroundStyle(.red)
                    .frame(width: 22)
                Text(title)
                    .font(.subheadline)
                    .multilineTextAlignment(.leading)
                Spacer(minLength: 0)
                Image(systemName: "arrow.up.left")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
            }
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color(uiColor: .tertiarySystemBackground), in: RoundedRectangle(cornerRadius: 14))
        }
        .buttonStyle(.plain)
    }

    private var composer: some View {
        HStack(alignment: .bottom, spacing: 10) {
            TextField("Converse com o ULTRON…", text: $draft, axis: .vertical)
                .font(.body)
                .lineLimit(1...5)
                .focused($composerFocused)
                .padding(.horizontal, 16)
                .padding(.vertical, 13)
                .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 23))
                .submitLabel(.send)
                .onSubmit(send)

            Button(action: send) {
                Image(systemName: isSending ? "hourglass" : "arrow.up")
                    .font(.system(size: 18, weight: .bold))
                    .foregroundStyle(.black)
                    .frame(width: 48, height: 48)
                    .background(Color.red, in: Circle())
            }
            .disabled(draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isSending)
            .opacity(draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isSending ? 0.45 : 1)
            .accessibilityLabel("Enviar mensagem")
        }
        .padding(.horizontal, 14)
        .padding(.top, 10)
        .padding(.bottom, 8)
        .background(.ultraThinMaterial)
        .overlay(alignment: .top) {
            Rectangle().fill(Color.white.opacity(0.07)).frame(height: 1)
        }
    }

    private func errorPanel(_ message: String) -> some View {
        HStack(alignment: .center, spacing: 10) {
            Image(systemName: "wifi.exclamationmark")
                .foregroundStyle(.red)
            Text(message)
                .font(.caption)
                .foregroundStyle(.primary)
                .frame(maxWidth: .infinity, alignment: .leading)
            if failedMessage != nil {
                Button("Tentar novamente") { retryFailedMessage() }
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.red)
            }
            Button {
                errorMessage = nil
            } label: {
                Image(systemName: "xmark")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.secondary)
            }
            .accessibilityLabel("Fechar aviso")
        }
        .padding(12)
        .background(Color.red.opacity(0.09), in: RoundedRectangle(cornerRadius: 14))
        .padding(.horizontal, 14)
        .padding(.bottom, 4)
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
        composerFocused = false
        messages.append(ChatMessage(role: .user, text: text))
        performSend(text)
    }

    private func retryFailedMessage() {
        guard let text = failedMessage, !isSending else { return }
        performSend(text)
    }

    private func performSend(_ text: String) {
        errorMessage = nil
        failedMessage = nil
        isSending = true
        checkingServer = true

        Task {
            do {
                let result = try await client.send(text, serverURL: serverURL)
                serverOnline = true
                checkingServer = false

                let assistantMessage = ChatMessage(
                    role: .assistant,
                    text: result.reply,
                    strategy: result.strategy
                )
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
                        errorMessage = "A resposta do FlyBrain foi mantida; a IA local não concluiu: \(error.localizedDescription)"
                    }
                }
            } catch {
                serverOnline = false
                checkingServer = false
                failedMessage = text
                errorMessage = error.localizedDescription
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

    private var isUser: Bool { message.role == .user }

    var body: some View {
        HStack(alignment: .bottom, spacing: 8) {
            if isUser { Spacer(minLength: 44) }
            VStack(alignment: .leading, spacing: 8) {
                Text(message.text)
                    .font(.body)
                    .lineSpacing(3)
                    .textSelection(.enabled)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 13)
                    .foregroundStyle(isUser ? Color.black : Color.primary)
                    .background(
                        isUser ? Color.red : Color(.secondarySystemBackground),
                        in: RoundedRectangle(cornerRadius: 20, style: .continuous)
                    )

                if !isUser, let strategy = message.strategy {
                    HStack(spacing: 10) {
                        Text("FlyBrain · \(strategy)")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                        Spacer()
                        if feedbackSent {
                            Label("Obrigado", systemImage: "checkmark")
                                .font(.caption2)
                                .foregroundStyle(.green)
                        } else {
                            Button {
                                submitFeedback(5, strategy)
                            } label: {
                                Image(systemName: "hand.thumbsup")
                            }
                            .accessibilityLabel("Resposta útil")
                            Button {
                                submitFeedback(1, strategy)
                            } label: {
                                Image(systemName: "hand.thumbsdown")
                            }
                            .accessibilityLabel("Resposta não útil")
                        }
                    }
                    .padding(.horizontal, 7)
                    if let feedbackError {
                        Text(feedbackError)
                            .font(.caption2)
                            .foregroundStyle(.red)
                            .padding(.horizontal, 7)
                    }
                }
            }
            if !isUser { Spacer(minLength: 44) }
        }
        .padding(.horizontal, 14)
        .frame(maxWidth: .infinity)
    }

    private func submitFeedback(_ rating: Int, _ strategy: String) {
        Task {
            do {
                try await onFeedback(rating, strategy)
                feedbackSent = true
                feedbackError = nil
            } catch {
                feedbackError = "Não foi possível enviar o feedback."
            }
        }
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
                Section("Servidor") {
                    TextField("https://ultron-api.onrender.com", text: $draftURL)
                        .keyboardType(.URL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    Text("O ULTRON verifica a conexão antes de cada mensagem e tenta recuperar falhas temporárias.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Section("Cérebro linguístico local") {
                    Text(localModel.isModelAvailable
                         ? "Qwen3 0.6B está instalado. FlyBrain continua sendo o núcleo central."
                         : "Baixe o modelo Qwen3 0.6B (~462 MiB). A geração acontece neste iPhone via Metal.")
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
            .onAppear { draftURL = serverURL }
        }
        .preferredColorScheme(.dark)
    }
}
