import Foundation

struct ChatMessage: Identifiable, Codable {
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

private struct ChatRequest: Encodable { let message: String }
private struct ChatResponse: Decodable { let reply: String; let strategy: String? }
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

    var errorDescription: String? {
        switch self {
        case .invalidServerURL: return "Configure o endereço HTTPS do servidor."
        case .invalidResponse: return "Resposta inválida do servidor."
        case .serverError(let code): return "O servidor respondeu com erro (\(code))."
        }
    }
}

private struct HealthResponse: Decodable { let status: String }

struct ChatClient {
    func checkHealth(serverURL: String) async -> Bool {
        guard let base = URL(string: serverURL), base.scheme == "https",
              let url = URL(string: "/health", relativeTo: base) else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = 12
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse,
                  (200..<300).contains(http.statusCode) else { return false }
            return (try? JSONDecoder().decode(HealthResponse.self, from: data).status) == "online"
        } catch {
            return false
        }
    }

    func send(_ message: String, serverURL: String) async throws -> ChatResult {
        guard let base = URL(string: serverURL), base.scheme == "https",
              let url = URL(string: "/chat", relativeTo: base) else {
            throw ChatClientError.invalidServerURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 90
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(ChatRequest(message: message))
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw ChatClientError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else { throw ChatClientError.serverError(http.statusCode) }
        let result = try JSONDecoder().decode(ChatResponse.self, from: data)
        return ChatResult(reply: result.reply, strategy: result.strategy)
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
