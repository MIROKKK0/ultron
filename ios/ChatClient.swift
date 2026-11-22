import Foundation

struct ChatMessage: Identifiable, Codable, Equatable {
    let id: UUID
    let role: Role
    let text: String
    let strategy: String?

    enum Role: String, Codable { case user, assistant }

    init(role: Role, text: String, strategy: String? = nil) {
        self.id = UUID()
        self.role = role
        self.text = text
        self.strategy = strategy
    }
}

private struct ChatRequest: Encodable {
    let message: String
    let history: [String]

    init(message: String, history: [String] = []) {
        self.message = message
        self.history = Array(history.suffix(8)).map { String($0.prefix(1000)) }
    }
}
private struct ChatResponse: Decodable { let reply: String; let strategy: String? }
private struct ChatStreamEvent: Decodable {
    let type: String
    let stage: String?
    let reply: String?
    let strategy: String?
    let status: Int?
}
private struct FeedbackRequest: Encodable {
    let rating: Int
    let strategy: String
    let comment: String
}

struct ChatResult { let reply: String; let strategy: String? }

enum ChatClientError: LocalizedError {
    case invalidServerURL
    case invalidResponse
    case serverError(Int)
    case missingAPIToken

    var errorDescription: String? {
        switch self {
        case .invalidServerURL: return "Configure o endereço HTTPS do servidor."
        case .invalidResponse: return "O servidor enviou uma resposta inválida."
        case .missingAPIToken: return "Adicione o token privado da API nas configurações do ULTRON."
        case .serverError(let code):
            if code == 404 {
                return "A rota de chat não existe nesta versão do servidor. Atualize o backend ou confira o endereço configurado."
            }
            if code == 503 {
                return "O servidor está temporariamente indisponível ou sem uma configuração necessária."
            }
            return "O servidor respondeu com erro (\(code))."
        }
    }
}

private struct HealthResponse: Decodable { let status: String }
private struct MemoryGraphResponse: Decodable {
    let nodes: [NeuralMemoryNode]
    let edges: [NeuralMemoryEdge]
}
private struct MemorySyncItem: Encodable {
    let id: String
    let content: String
    let kind: String
    let importance: Int
    let source: String
    let created_at: String
    let updated_at: String
}
private struct MemorySyncRequest: Encodable {
    let installation_id: String
    let memories: [MemorySyncItem]
    let replace: Bool
}

struct ChatClient {
    private func endpoint(_ path: String, serverURL: String) -> URL? {
        guard let base = URL(string: serverURL.trimmingCharacters(in: .whitespacesAndNewlines)),
              base.scheme?.lowercased() == "https",
              base.host != nil else { return nil }
        return URL(string: path, relativeTo: base)?.absoluteURL
    }

    func checkHealth(serverURL: String) async -> Bool {
        // The health endpoint is preferred; the root route is a compatibility fallback.
        for path in ["/health", "/"] {
            guard let url = endpoint(path, serverURL: serverURL) else { return false }
            var request = URLRequest(url: url)
            request.httpMethod = "GET"
            request.timeoutInterval = 12
            do {
                let (data, response) = try await URLSession.shared.data(for: request)
                guard let http = response as? HTTPURLResponse,
                      (200..<300).contains(http.statusCode) else { continue }
                if (try? JSONDecoder().decode(HealthResponse.self, from: data).status) == "online" {
                    return true
                }
            } catch {
                continue
            }
        }
        return false
    }

    private func sendLegacy(_ message: String, history: [String], serverURL: String) async throws -> ChatResult {
        guard let url = endpoint("/chat", serverURL: serverURL) else {
            throw ChatClientError.invalidServerURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 90
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(ChatRequest(message: message, history: history))
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw ChatClientError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else {
            throw ChatClientError.serverError(http.statusCode)
        }
        let decoded = try JSONDecoder().decode(ChatResponse.self, from: data)
        return ChatResult(reply: decoded.reply, strategy: decoded.strategy)
    }

    func send(
        _ message: String,
        serverURL: String,
        history: [String] = [],
        onPhase: @MainActor @escaping (BrainPhase) -> Void = { _ in }
    ) async throws -> ChatResult {
        guard let url = endpoint("/chat/stream", serverURL: serverURL) else {
            throw ChatClientError.invalidServerURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 90
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
        request.httpBody = try JSONEncoder().encode(ChatRequest(message: message, history: history))

        let (bytes, response) = try await URLSession.shared.bytes(for: request)
        guard let http = response as? HTTPURLResponse else { throw ChatClientError.invalidResponse }

        // Older Render deploys may not have /chat/stream yet. Fall back to /chat,
        // which exists in the previous production API and returns the same payload.
        if http.statusCode == 404 {
            await onPhase(.processing)
            let result = try await sendLegacy(message, history: history, serverURL: serverURL)
            await onPhase(.responding)
            return result
        }
        guard (200..<300).contains(http.statusCode) else {
            throw ChatClientError.serverError(http.statusCode)
        }

        for try await line in bytes.lines {
            guard line.hasPrefix("data:") else { continue }
            let payload = String(line.dropFirst(5)).trimmingCharacters(in: .whitespaces)
            guard let data = payload.data(using: .utf8) else { continue }
            let event = try JSONDecoder().decode(ChatStreamEvent.self, from: data)
            switch event.type {
            case "stage":
                if event.stage == "processing" {
                    await onPhase(.processing)
                } else if event.stage == "responding" {
                    await onPhase(.responding)
                }
            case "final":
                guard let reply = event.reply else { throw ChatClientError.invalidResponse }
                return ChatResult(reply: reply, strategy: event.strategy)
            case "error":
                throw ChatClientError.serverError(event.status ?? 500)
            default:
                continue
            }
        }
        throw ChatClientError.invalidResponse
    }

    private func authenticatedRequest(path: String, serverURL: String) throws -> URLRequest {
        guard let base = URL(string: serverURL.trimmingCharacters(in: .whitespacesAndNewlines)),
              var components = URLComponents(url: base, resolvingAgainstBaseURL: false),
              base.scheme?.lowercased() == "https" else {
            throw ChatClientError.invalidServerURL
        }
        components.path = path
        guard let url = components.url else { throw ChatClientError.invalidServerURL }
        guard let token = KeychainStore.read("api_token"), !token.isEmpty else {
            throw ChatClientError.missingAPIToken
        }
        var request = URLRequest(url: url)
        request.setValue("Bearer \\(token)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 30
        return request
    }

    func fetchMemoryGraph(serverURL: String, installationID: String) async throws -> (nodes: [NeuralMemoryNode], edges: [NeuralMemoryEdge]) {
        var request = try authenticatedRequest(path: "/api/memory/graph", serverURL: serverURL)
        guard var components = URLComponents(url: request.url!, resolvingAgainstBaseURL: false) else {
            throw ChatClientError.invalidServerURL
        }
        components.queryItems = [URLQueryItem(name: "installation_id", value: installationID)]
        request.url = components.url
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw ChatClientError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else { throw ChatClientError.serverError(http.statusCode) }
        let graph = try JSONDecoder().decode(MemoryGraphResponse.self, from: data)
        return (graph.nodes, graph.edges)
    }

    func syncMemories(_ messages: [ChatMessage], serverURL: String, installationID: String) async throws {
        let now = ISO8601DateFormatter().string(from: Date())
        let items = messages.suffix(60).map { message in
            MemorySyncItem(
                id: message.id.uuidString,
                content: String(message.text.prefix(4000)),
                kind: message.role.rawValue,
                importance: message.role == .user ? 3 : 2,
                source: "ios-chat",
                created_at: now,
                updated_at: now
            )
        }
        var request = try authenticatedRequest(path: "/api/memory/sync", serverURL: serverURL)
        request.httpMethod = "POST"
        request.httpBody = try JSONEncoder().encode(
            MemorySyncRequest(installation_id: installationID, memories: items, replace: true)
        )
        let (_, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw ChatClientError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else { throw ChatClientError.serverError(http.statusCode) }
    }

    func sendFeedback(_ rating: Int, strategy: String, serverURL: String) async throws {
        guard let url = endpoint("/feedback", serverURL: serverURL) else {
            throw ChatClientError.invalidServerURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 20
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(
            FeedbackRequest(rating: rating, strategy: strategy, comment: "")
        )
        let (_, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw ChatClientError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else { throw ChatClientError.serverError(http.statusCode) }
    }
}
