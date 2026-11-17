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
private struct ChatStreamEvent: Decodable {
    let type: String
    let stage: String?
    let reply: String?
    let strategy: String?
    let detail: String?
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

    var errorDescription: String? {
        switch self {
        case .invalidServerURL: return "Configure o endereço HTTPS do servidor."
        case .invalidResponse: return "Resposta inválida do servidor."
        case .serverError(let code): return "O servidor respondeu com erro (\(code))."
        }
    }
}

struct ChatClient {
    func send(
        _ message: String,
        serverURL: String,
        onPhase: @MainActor @escaping (BrainPhase) -> Void = { _ in }
    ) async throws -> ChatResult {
        guard let base = URL(string: serverURL), base.scheme == "https",
              let url = URL(string: "/chat/stream", relativeTo: base) else {
            throw ChatClientError.invalidServerURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 60
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
        request.httpBody = try JSONEncoder().encode(ChatRequest(message: message))

        let (bytes, response) = try await URLSession.shared.bytes(for: request)
        guard let http = response as? HTTPURLResponse else { throw ChatClientError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else {
            throw ChatClientError.serverError(http.statusCode)
        }

        for try await line in bytes.lines {
            guard line.hasPrefix("data:") else { continue }
            let payload = line.dropFirst(5).trimmingCharacters(in: .whitespaces)
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

