import Foundation

struct ChatMessage: Identifiable, Codable {
    let id: UUID
    let role: Role
    let text: String

    enum Role: String, Codable {
        case user
        case assistant
    }

    init(role: Role, text: String) {
        self.id = UUID()
        self.role = role
        self.text = text
    }
}

private struct ChatRequest: Encodable {
    let message: String
}

private struct ChatResponse: Decodable {
    let reply: String
}

enum ChatClientError: LocalizedError {
    case invalidServerURL
    case invalidResponse
    case serverError(Int)

    var errorDescription: String? {
        switch self {
        case .invalidServerURL: return "Configure o endereço HTTPS do servidor nas configurações."
        case .invalidResponse: return "Resposta inválida do servidor."
        case .serverError(let code): return "O servidor respondeu com erro (\(code))."
        }
    }
}

struct ChatClient {
    func send(_ message: String, serverURL: String) async throws -> String {
        guard let base = URL(string: serverURL),
              base.scheme == "https",
              let url = URL(string: "/chat", relativeTo: base) else {
            throw ChatClientError.invalidServerURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 45
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(ChatRequest(message: message))

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw ChatClientError.invalidResponse
        }
        guard (200..<300).contains(http.statusCode) else {
            throw ChatClientError.serverError(http.statusCode)
        }
        return try JSONDecoder().decode(ChatResponse.self, from: data).reply
    }
}
