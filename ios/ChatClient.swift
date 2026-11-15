import Foundation

struct ChatMessage: Identifiable, Codable {
    let id: UUID
    let role: Role
    var text: String
    let strategy: String?
    var diagnostics: String?

    enum Role: String, Codable { case user, assistant }

    init(role: Role, text: String, strategy: String? = nil, diagnostics: String? = nil) {
        self.id = UUID()
        self.role = role
        self.text = text
        self.strategy = strategy
        self.diagnostics = diagnostics
    }
}

private struct ChatRequest: Encodable { let message: String }
private struct ChatResponse: Decodable {
    let reply: String
    let strategy: String?
    let brainContext: BrainContext?
    let timingsMS: [String: Double]?

    enum CodingKeys: String, CodingKey {
        case reply, strategy
        case brainContext = "brain_context"
        case timingsMS = "timings_ms"
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
    let timingsMS: [String: Double]
    let networkRoundTripMS: Double
}

enum ChatClientError: LocalizedError {
    case invalidServerURL
    case invalidResponse
    case serverError(Int, String?)
    case connectionFailed(String)

    var errorDescription: String? {
        switch self {
        case .invalidServerURL:
            return "Endereço do servidor inválido. Abra as configurações e confira a URL HTTPS."
        case .invalidResponse:
            return "O servidor respondeu em um formato inesperado."
        case .serverError(let code, let detail):
            return detail ?? "O servidor respondeu com erro HTTP \(code)."
        case .connectionFailed(let detail):
            return detail
        }
    }
}

struct ChatClient {
    private func endpoint(_ path: String, serverURL: String) throws -> URL {
        guard let base = URL(string: serverURL.trimmingCharacters(in: .whitespacesAndNewlines)),
              base.scheme == "https", base.host != nil,
              let url = URL(string: path, relativeTo: base)?.absoluteURL else {
            throw ChatClientError.invalidServerURL
        }
        return url
    }

    /// Render Free can sleep. Wake it immediately before the chat request,
    /// rather than only once when the app launches.
    @discardableResult
    func warmUp(serverURL: String) async -> Bool {
        guard let url = try? endpoint("/health", serverURL: serverURL) else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = 150
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        for attempt in 0..<3 {
            do {
                let (_, response) = try await URLSession.shared.data(for: request)
                if let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) {
                    return true
                }
            } catch {
                if !Self.isTransient(error) { return false }
            }
            if attempt < 2 {
                try? await Task.sleep(nanoseconds: UInt64(attempt + 1) * 1_000_000_000)
            }
        }
        return false
    }

    func send(_ message: String, serverURL: String) async throws -> ChatResult {
        let url = try endpoint("/chat", serverURL: serverURL)

        // Send directly to /chat. A separate /health round-trip before every
        // message adds latency and cannot prevent Render from sleeping again.
        // The chat request itself wakes a sleeping instance; transient failures
        // are retried below.
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 180
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue(UUID().uuidString, forHTTPHeaderField: "X-Request-ID")
        request.httpBody = try JSONEncoder().encode(ChatRequest(message: message))

        var lastError: Error?
        for attempt in 0..<3 {
            do {
                let requestStartedAt = Date()
                let (data, response) = try await URLSession.shared.data(for: request)
                let networkRoundTripMS = Date().timeIntervalSince(requestStartedAt) * 1000
                guard let http = response as? HTTPURLResponse else {
                    throw ChatClientError.invalidResponse
                }
                guard (200..<300).contains(http.statusCode) else {
                    let detail = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
                    let message = detail?["detail"] as? String
                    throw ChatClientError.serverError(http.statusCode, message)
                }
                let result = try JSONDecoder().decode(ChatResponse.self, from: data)
                return ChatResult(
                    reply: result.reply,
                    strategy: result.strategy,
                    brainContext: result.brainContext,
                    timingsMS: result.timingsMS ?? [:],
                    networkRoundTripMS: networkRoundTripMS
                )
            } catch {
                lastError = error
                guard Self.isTransient(error), attempt < 2 else { throw Self.presentable(error) }
                try? await Task.sleep(nanoseconds: UInt64(attempt + 1) * 1_000_000_000)
            }
        }
        throw Self.presentable(lastError ?? ChatClientError.invalidResponse)
    }

    func sendFeedback(_ rating: Int, strategy: String, serverURL: String) async throws {
        let url = try endpoint("/feedback", serverURL: serverURL)
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 30
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(
            FeedbackRequest(rating: rating, strategy: strategy, comment: "")
        )
        let (_, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw ChatClientError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else {
            throw ChatClientError.serverError(http.statusCode, nil)
        }
    }

    private static func isTransient(_ error: Error) -> Bool {
        let nsError = error as NSError
        guard nsError.domain == NSURLErrorDomain else { return false }
        let code = URLError.Code(rawValue: nsError.code)
        return [
            .timedOut, .cannotFindHost, .cannotConnectToHost,
            .networkConnectionLost, .notConnectedToInternet,
            .dnsLookupFailed, .internationalRoamingOff,
            .dataNotAllowed, .secureConnectionFailed
        ].contains(code)
    }

    private static func presentable(_ error: Error) -> Error {
        if let known = error as? ChatClientError { return known }
        let nsError = error as NSError
        if nsError.domain == NSURLErrorDomain {
            switch URLError.Code(rawValue: nsError.code) {
            case .notConnectedToInternet:
                return ChatClientError.connectionFailed("Seu iPhone está sem conexão com a internet.")
            case .timedOut:
                return ChatClientError.connectionFailed("O servidor demorou demais para responder. Tente novamente.")
            case .networkConnectionLost:
                return ChatClientError.connectionFailed("A conexão caiu durante o envio. Sua mensagem pode ser reenviada.")
            default:
                return ChatClientError.connectionFailed("Não consegui alcançar o servidor: \(nsError.localizedDescription)")
            }
        }
        return error
    }
}
