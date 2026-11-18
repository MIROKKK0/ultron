import SwiftUI

struct ContentView: View {
    @AppStorage("ultronServerURL") private var serverURL = "https://ultron-api-c5ae.onrender.com"
    @AppStorage("ultronChatHistoryData") private var storedChatHistory: Data = Data()
    @State private var messages: [ChatMessage] = [
        ChatMessage(role: .assistant, text: "Olá. Sou o ULTRON. Meu classificador próprio e minhas habilidades locais estão disponíveis. Use /plan, /research, /calc, /self ou /skills. A geração livre ainda está em desenvolvimento.")
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
                    UltronBrainDisplay(isActive: isSending, phase: brainPhase.title)
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
                SettingsView(serverURL: $serverURL, onClearHistory: clearLocalHistory)
                    .presentationDetents([.medium, .large])
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
                let result = try await client.send(text, serverURL: serverURL, history: recentHistory) { phase in
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


/// Human-brain silhouette with a low-power ambient pulse.
/// Activity accelerates only while the real request pipeline is running.
private struct UltronBrainDisplay: View {
    let isActive: Bool
    let phase: String

    var body: some View {
        VStack(spacing: 3) {
            TimelineView(.animation(minimumInterval: 1.0 / 12.0, paused: false)) { timeline in
                let time = timeline.date.timeIntervalSinceReferenceDate
                Canvas { context, size in
                    drawBrain(in: &context, size: size, time: time, active: isActive)
                }
                .frame(width: 76, height: 62)
            }
            Text(isActive ? phase : "monitorando")
                .font(.system(size: 8, weight: .medium, design: .rounded))
                .foregroundStyle(isActive ? Color.cyan : Color.secondary)
                .lineLimit(1)
                .frame(width: 82)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(isActive ? "Cérebro neural ativo: \(phase)" : "Cérebro neural em monitoramento")
    }

    private func drawBrain(
        in context: inout GraphicsContext,
        size: CGSize,
        time: TimeInterval,
        active: Bool
    ) {
        let scale = CGAffineTransform(scaleX: size.width, y: size.height)
        let speed = active ? 2.8 : 0.55
        let pulse = 0.5 + 0.5 * sin(time * speed)

        // Two joined hemispheres form a recognizable anatomical silhouette.
        var outline = Path()
        outline.move(to: CGPoint(x: 0.50, y: 0.15))
        outline.addCurve(to: CGPoint(x: 0.10, y: 0.43),
                        control1: CGPoint(x: 0.30, y: 0.00),
                        control2: CGPoint(x: 0.08, y: 0.17))
        outline.addCurve(to: CGPoint(x: 0.22, y: 0.83),
                        control1: CGPoint(x: 0.00, y: 0.61),
                        control2: CGPoint(x: 0.10, y: 0.82))
        outline.addCurve(to: CGPoint(x: 0.49, y: 0.91),
                        control1: CGPoint(x: 0.30, y: 0.97),
                        control2: CGPoint(x: 0.42, y: 0.98))
        outline.addCurve(to: CGPoint(x: 0.78, y: 0.83),
                        control1: CGPoint(x: 0.58, y: 0.98),
                        control2: CGPoint(x: 0.70, y: 0.97))
        outline.addCurve(to: CGPoint(x: 0.90, y: 0.43),
                        control1: CGPoint(x: 0.90, y: 0.82),
                        control2: CGPoint(x: 1.00, y: 0.61))
        outline.addCurve(to: CGPoint(x: 0.50, y: 0.15),
                        control1: CGPoint(x: 0.92, y: 0.17),
                        control2: CGPoint(x: 0.70, y: 0.00))
        outline.closeSubpath()
        outline = outline.applying(scale)

        let glow = Color.cyan.opacity(active ? 0.28 + pulse * 0.35 : 0.12 + pulse * 0.08)
        context.fill(outline, with: .color(Color.cyan.opacity(0.07)))
        context.stroke(outline, with: .color(glow), lineWidth: 1.5)

        // Central fissure separates the hemispheres.
        var fissure = Path()
        fissure.move(to: CGPoint(x: 0.50, y: 0.16))
        fissure.addCurve(to: CGPoint(x: 0.50, y: 0.88),
                         control1: CGPoint(x: 0.46, y: 0.37),
                         control2: CGPoint(x: 0.54, y: 0.62))
        context.stroke(fissure.applying(scale),
                       with: .color(Color.cyan.opacity(0.48)),
                       style: StrokeStyle(lineWidth: 0.8, dash: [2, 2]))

        // Cortical folds: paired curved grooves, not random decorative rings.
        let folds: [[CGPoint]] = [
            [CGPoint(x: 0.15, y: 0.36), CGPoint(x: 0.27, y: 0.23), CGPoint(x: 0.39, y: 0.34)],
            [CGPoint(x: 0.12, y: 0.53), CGPoint(x: 0.25, y: 0.42), CGPoint(x: 0.40, y: 0.52)],
            [CGPoint(x: 0.18, y: 0.69), CGPoint(x: 0.29, y: 0.59), CGPoint(x: 0.43, y: 0.68)],
            [CGPoint(x: 0.85, y: 0.36), CGPoint(x: 0.73, y: 0.23), CGPoint(x: 0.61, y: 0.34)],
            [CGPoint(x: 0.88, y: 0.53), CGPoint(x: 0.75, y: 0.42), CGPoint(x: 0.60, y: 0.52)],
            [CGPoint(x: 0.82, y: 0.69), CGPoint(x: 0.71, y: 0.59), CGPoint(x: 0.57, y: 0.68)]
        ]
        for points in folds {
            var groove = Path()
            groove.move(to: points[0])
            groove.addQuadCurve(to: points[2], control: points[1])
            context.stroke(groove.applying(scale),
                           with: .color(Color.cyan.opacity(0.42)),
                           style: StrokeStyle(lineWidth: 0.9, lineCap: .round))
        }

        // Neural links and firing points pulse faster during real inference.
        let nodes: [CGPoint] = [
            CGPoint(x: 0.20, y: 0.34), CGPoint(x: 0.31, y: 0.29),
            CGPoint(x: 0.39, y: 0.46), CGPoint(x: 0.25, y: 0.59),
            CGPoint(x: 0.36, y: 0.73), CGPoint(x: 0.61, y: 0.30),
            CGPoint(x: 0.72, y: 0.35), CGPoint(x: 0.78, y: 0.55),
            CGPoint(x: 0.64, y: 0.66), CGPoint(x: 0.52, y: 0.48)
        ]
        let links = [(0, 1), (1, 2), (2, 3), (3, 4), (2, 9),
                     (9, 5), (5, 6), (6, 7), (7, 8), (8, 9), (1, 5), (3, 8)]
        for (index, pair) in links.enumerated() {
            var link = Path()
            link.move(to: nodes[pair.0])
            link.addLine(to: nodes[pair.1])
            let signal = 0.12 + 0.55 * (0.5 + 0.5 * sin(time * speed + Double(index) * 0.83))
            context.stroke(link.applying(scale),
                           with: .color(Color.cyan.opacity(active ? signal : signal * 0.42)),
                           lineWidth: 0.7)
        }
        for (index, point) in nodes.enumerated() {
            let firing = 0.5 + 0.5 * sin(time * speed + Double(index) * 1.17)
            let radius = active ? 1.8 + firing * 2.0 : 1.2 + firing * 0.8
            let rect = CGRect(
                x: point.x * size.width - radius,
                y: point.y * size.height - radius,
                width: radius * 2,
                height: radius * 2
            )
            context.fill(Path(ellipseIn: rect),
                         with: .color(Color.cyan.opacity(active ? 0.45 + firing * 0.55 : 0.25 + firing * 0.25)))
        }
    }
}
