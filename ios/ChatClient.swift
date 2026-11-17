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
    let status: Int?
}
private struct InstallationRegistration: Decodable {
    let installation_id: String
    let access_token: String
}

private struct MemoryRequest: Encodable { let content: String }
private struct MemoryCreated: Decodable { let id: Int }
private struct MemoryItem: Decodable {
    let id: Int
    let content: String
    let created_at: String
}
private struct MemoryList: Decodable { let items: [MemoryItem] }

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
        case .invalidResponse: return "O servidor enviou uma resposta inválida."
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

    private func sendLegacy(_ message: String, serverURL: String) async throws -> ChatResult {
        guard let url = endpoint("/chat", serverURL: serverURL) else {
            throw ChatClientError.invalidServerURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 90
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(ChatRequest(message: message))
        if let token = try? InstallationCredentialStore.read() {
            request.setValue("Bearer \\(token)", forHTTPHeaderField: "Authorization")
        }
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
        request.httpBody = try JSONEncoder().encode(ChatRequest(message: message))

        let (bytes, response) = try await URLSession.shared.bytes(for: request)
        guard let http = response as? HTTPURLResponse else { throw ChatClientError.invalidResponse }

        // Older Render deploys may not have /chat/stream yet. Fall back to /chat,
        // which exists in the previous production API and returns the same payload.
        if http.statusCode == 404 {
            await onPhase(.processing)
            let result = try await sendLegacy(message, serverURL: serverURL)
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


    private func installationToken(serverURL: String) async throws -> String {
        if let existing = try InstallationCredentialStore.read() { return existing }
        guard let url = endpoint("/installations/register", serverURL: serverURL) else {
            throw ChatClientError.invalidServerURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 20
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw ChatClientError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else {
            throw InstallationCredentialError.serverError(http.statusCode)
        }
        let registration = try JSONDecoder().decode(InstallationRegistration.self, from: data)
        try InstallationCredentialStore.save(registration.access_token)
        return registration.access_token
    }

    private func memoryRequest(
        path: String,
        method: String,
        serverURL: String,
        body: MemoryRequest? = nil
    ) async throws -> Data {
        guard let url = endpoint(path, serverURL: serverURL) else {
            throw ChatClientError.invalidServerURL
        }
        let token = try await installationToken(serverURL: serverURL)
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = 20
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONEncoder().encode(body)
        }
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw ChatClientError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else {
            throw InstallationCredentialError.serverError(http.statusCode)
        }
        return data
    }

    func remember(_ content: String, serverURL: String) async throws -> Int {
        let data = try await memoryRequest(
            path: "/memory",
            method: "POST",
            serverURL: serverURL,
            body: MemoryRequest(content: content)
        )
        return try JSONDecoder().decode(MemoryCreated.self, from: data).id
    }

    func listMemories(serverURL: String) async throws -> [String] {
        let data = try await memoryRequest(path: "/memory", method: "GET", serverURL: serverURL)
        let result = try JSONDecoder().decode(MemoryList.self, from: data)
        return result.items.map { "[\($0.id)] \($0.content)" }
    }

    func forgetMemory(_ id: Int, serverURL: String) async throws {
        _ = try await memoryRequest(path: "/memory/\(id)", method: "DELETE", serverURL: serverURL)
    }

    func revokeInstallation(serverURL: String) async throws {
        _ = try await memoryRequest(path: "/installation", method: "DELETE", serverURL: serverURL)
        try InstallationCredentialStore.delete()
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
