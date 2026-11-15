import Foundation

struct ChatMessage: Identifiable, Codable {
    let id: UUID
    let role: Role
    var text: String
    let strategy: String?

    enum Role: String, Codable { case user, assistant }

    init(role: Role, text: String, strategy: String? = nil) {
        self.id = UUID()
        self.role = role
        self.text = text
        self.strategy = strategy
    }
}

private struct ChatRequest: Encodable { let message: String }
private struct ChatResponse: Decodable {
    let reply: String
    let strategy: String?
    let brainContext: BrainContext?

    enum CodingKeys: String, CodingKey {
        case reply, strategy
        case brainContext = "brain_context"
    }
}
private struct FeedbackRequest: Encodable {
    let rating: Int
    let strategy: String
    let comment: String
}

struct BrainContext: Decodable {
    let core: String
    let runtime: String
    let isFullConnectome: Bool
    let novelty: Double
    let groupActivity: [String: Double]
    let roleScores: [String: Double]

    enum CodingKeys: String, CodingKey {
        case core, runtime, novelty
        case isFullConnectome = "is_full_connectome"
        case groupActivity = "group_activity"
        case roleScores = "role_scores"
    }
}

struct ChatResult {
    let reply: String
    let strategy: String?
    let brainContext: BrainContext?
}

enum ChatClientError: LocalizedError {
    case invalidServerURL
    case invalidResponse
    case serverError(Int)

    var errorDescription: String? {
        switch self {
        case .invalidServerURL: return "Configure o endereço HTTPS do servidor."
        case .invalidResponse: return "Resposta inválida do servidor."
        case .serverError(let code): return "O servidor respondeu com erro (\(code))."
        }
    }
}

struct ChatClient {
    /// Wake a sleeping free-tier Render instance before the user sends a message.
    func warmUp(serverURL: String) async {
        guard let base = URL(string: serverURL), base.scheme == "https",
              let url = URL(string: "/health", relativeTo: base) else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = 25
        request.cachePolicy = .reloadIgnoringLocalCacheData
        _ = try? await URLSession.shared.data(for: request)
    }

    func send(_ message: String, serverURL: String) async throws -> ChatResult {
        guard let base = URL(string: serverURL), base.scheme == "https",
              let url = URL(string: "/chat", relativeTo: base) else {
            throw ChatClientError.invalidServerURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 60
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(ChatRequest(message: message))
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw ChatClientError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else { throw ChatClientError.serverError(http.statusCode) }
        let result = try JSONDecoder().decode(ChatResponse.self, from: data)
        return ChatResult(reply: result.reply, strategy: result.strategy, brainContext: result.brainContext)
    }

    func sendFeedback(_ rating: Int, strategy: String, serverURL: String) async throws {
        guard let base = URL(string: serverURL), base.scheme == "https",
              let url = URL(string: "/feedback", relativeTo: base) else {
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
