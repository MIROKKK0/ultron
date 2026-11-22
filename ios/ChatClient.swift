import Foundation

struct ChatMessage: Identifiable, Codable, Equatable {
    let id: UUID
    let role: Role
    let text: String
    let strategy: String?
    let createdAt: Date?

    enum Role: String, Codable { case user, assistant }

    init(role: Role, text: String, strategy: String? = nil) {
        self.id = UUID()
        self.role = role
        self.text = text
        self.strategy = strategy
        self.createdAt = Date()
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

private struct BrainRunRequest: Encodable {
    let goal: String
    let history: [String]

    init(goal: String, history: [String]) {
        self.goal = goal
        self.history = Array(history.suffix(8)).map { String($0.prefix(1000)) }
    }
}

private struct BrainRunResponse: Decodable { let synthesis: String }
private struct ChatResponse: Decodable { let reply: String; let strategy: String? }
private struct ChatStreamEvent: Decodable {
    let type: String
    let stage: String?
    let reply: String?
    let strategy: String?
    let status: Int?
}

private struct InstallationRegistrationRequest: Encodable {
    let installation_id: String
    let installation_token: String
}

private struct TypedMemoryRequest: Encodable {
    let kind: String
    let content: String
    let source: String
    let confidence: Double
}

private struct MemoryCreated: Decodable { let id: Int }
private struct MemoryItem: Decodable {
    let id: Int
    let content: String
    let created_at: String?
}
private struct MemoryList: Decodable { let items: [MemoryItem] }

struct HistoryExportRecord: Encodable {
    let role: String
    let content: String
    let timestamp: String
}

private struct HistoryImportRequest: Encodable {
    let source_export: String
    let records: [HistoryExportRecord]
}

struct HistoryImportResult: Decodable {
    let imported: Int
    let duplicates: Int
    let scope: String
    let source: String
}

struct MemorySyncReport {
    let uploaded: Int
    let remaining: Int
}

enum MemoryWriteOutcome {
    case synced(serverID: Int)
    case queued(localID: UUID)
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
        case .invalidResponse: return "O servidor enviou uma resposta inválida."
        case .serverError(let code):
            if code == 401 { return "A credencial privada desta instalação foi recusada." }
            if code == 404 { return "A rota necessária não existe nesta versão do servidor." }
            if code == 503 { return "O servidor está temporariamente indisponível ou sem uma configuração necessária." }
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

    private func registerInstallationIfNeeded(serverURL: String) async throws -> InstallationCredentials {
        var credentials = try InstallationCredentialStore.loadOrCreate()
        guard !credentials.registered else { return credentials }
        guard let url = endpoint("/v2/installations/register", serverURL: serverURL) else {
            throw ChatClientError.invalidServerURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 20
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(
            InstallationRegistrationRequest(
                installation_id: credentials.id,
                installation_token: credentials.token
            )
        )
        let (_, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw ChatClientError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else { throw ChatClientError.serverError(http.statusCode) }
        credentials.registered = true
        try InstallationCredentialStore.save(credentials)
        return credentials
    }

    func authenticatedData(
        path: String,
        method: String,
        serverURL: String,
        body: Data? = nil
    ) async throws -> Data {
        let credentials = try await registerInstallationIfNeeded(serverURL: serverURL)
        guard let url = endpoint(path, serverURL: serverURL) else { throw ChatClientError.invalidServerURL }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = 90
        request.setValue(credentials.id, forHTTPHeaderField: "X-Installation-ID")
        request.setValue(credentials.token, forHTTPHeaderField: "X-Installation-Token")
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = body
        }
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw ChatClientError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else { throw ChatClientError.serverError(http.statusCode) }
        return data
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
        guard (200..<300).contains(http.statusCode) else { throw ChatClientError.serverError(http.statusCode) }
        let decoded = try JSONDecoder().decode(ChatResponse.self, from: data)
        return ChatResult(reply: decoded.reply, strategy: decoded.strategy)
    }

    private func sendLegacyStream(
        _ message: String,
        history: [String],
        serverURL: String,
        onPhase: @MainActor @escaping (BrainPhase) -> Void
    ) async throws -> ChatResult {
        guard let url = endpoint("/chat/stream", serverURL: serverURL) else {
            return try await sendLegacy(message, history: history, serverURL: serverURL)
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 90
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
        request.httpBody = try JSONEncoder().encode(ChatRequest(message: message, history: history))
        let (bytes, response) = try await URLSession.shared.bytes(for: request)
        guard let http = response as? HTTPURLResponse else { throw ChatClientError.invalidResponse }
        if http.statusCode == 404 {
            await onPhase(.processing)
            let result = try await sendLegacy(message, history: history, serverURL: serverURL)
            await onPhase(.responding)
            return result
        }
        guard (200..<300).contains(http.statusCode) else { throw ChatClientError.serverError(http.statusCode) }

        for try await line in bytes.lines {
            guard line.hasPrefix("data:") else { continue }
            let payload = String(line.dropFirst(5)).trimmingCharacters(in: .whitespaces)
            guard let data = payload.data(using: .utf8) else { continue }
            let event = try JSONDecoder().decode(ChatStreamEvent.self, from: data)
            switch event.type {
            case "stage":
                if event.stage == "processing" { await onPhase(.processing) }
                else if event.stage == "responding" { await onPhase(.responding) }
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

    func send(
        _ message: String,
        serverURL: String,
        history: [String] = [],
        onPhase: @MainActor @escaping (BrainPhase) -> Void = { _ in }
    ) async throws -> ChatResult {
        await onPhase(.connecting)
        // Opportunistically flush previously queued writes; failures leave them encrypted locally.
        _ = try? await syncQueuedMemories(serverURL: serverURL)
        do {
            let body = try JSONEncoder().encode(BrainRunRequest(goal: message, history: history))
            await onPhase(.processing)
            let data = try await authenticatedData(
                path: "/v2/brain/run",
                method: "POST",
                serverURL: serverURL,
                body: body
            )
            let result = try JSONDecoder().decode(BrainRunResponse.self, from: data)
            await onPhase(.responding)
            return ChatResult(reply: result.synthesis, strategy: nil)
        } catch ChatClientError.serverError(404) {
            // Older deployments keep working while the v2 API is rolling out.
            return try await sendLegacyStream(message, history: history, serverURL: serverURL, onPhase: onPhase)
        }
    }

    func remember(_ content: String, kind: String = "semantic", serverURL: String) async throws -> Int {
        let body = try JSONEncoder().encode(
            TypedMemoryRequest(kind: kind, content: content, source: "user_explicit", confidence: 1.0)
        )
        let data = try await authenticatedData(path: "/v2/memory", method: "POST", serverURL: serverURL, body: body)
        return try JSONDecoder().decode(MemoryCreated.self, from: data).id
    }

    func listMemories(serverURL: String) async throws -> [String] {
        let data = try await authenticatedData(path: "/v2/memory", method: "GET", serverURL: serverURL)
        let result = try JSONDecoder().decode(MemoryList.self, from: data)
        return result.items.map { "[\($0.id)] \($0.content)" }
    }

    func forgetMemory(_ id: Int, serverURL: String) async throws {
        _ = try await authenticatedData(path: "/v2/memory/\(id)", method: "DELETE", serverURL: serverURL)
    }

    /// Save immediately when online; queue only transient network/server failures.
    func rememberWithOfflineQueue(_ content: String, kind: String = "semantic",
                                  serverURL: String) async throws -> MemoryWriteOutcome {
        do {
            let serverID = try await remember(content, kind: kind, serverURL: serverURL)
            return .synced(serverID: serverID)
        } catch let error as ChatClientError {
            if case .serverError(let code) = error, code >= 500 {
                let id = try await OfflineMemoryQueue.shared.enqueue(
                    kind: kind, content: content, source: "offline_user_explicit", confidence: 1.0
                )
                return .queued(localID: id)
            }
            throw error
        } catch let error as URLError {
            let id = try await OfflineMemoryQueue.shared.enqueue(
                kind: kind, content: content, source: "offline_user_explicit", confidence: 1.0
            )
            return .queued(localID: id)
        }
    }

    /// Flush acknowledged items only; unacknowledged entries remain encrypted locally.
    func syncQueuedMemories(serverURL: String) async throws -> MemorySyncReport {
        let queue = OfflineMemoryQueue.shared
        let entries = try await queue.pending()
        var acknowledged = Set<UUID>()
        for entry in entries {
            let body = try JSONEncoder().encode(
                TypedMemoryRequest(kind: entry.kind, content: entry.content,
                                   source: entry.source, confidence: entry.confidence)
            )
            _ = try await authenticatedData(path: "/v2/memory", method: "POST",
                                            serverURL: serverURL, body: body)
            acknowledged.insert(entry.id)
        }
        try await queue.remove(acknowledged)
        return MemorySyncReport(uploaded: acknowledged.count, remaining: try await queue.count())
    }

    /// Import an explicit export while preserving the original role and timestamp.
    func importHistory(sourceExport: String, records: [HistoryExportRecord],
                       serverURL: String) async throws -> HistoryImportResult {
        let body = try JSONEncoder().encode(
            HistoryImportRequest(source_export: sourceExport, records: records)
        )
        let data = try await authenticatedData(path: "/v2/memory/import", method: "POST",
                                               serverURL: serverURL, body: body)
        return try JSONDecoder().decode(HistoryImportResult.self, from: data)
    }

    func reaTools(serverURL: String) async throws -> Data {
        try await authenticatedData(
            path: "/v2/reverse-engineering/tools",
            method: "GET",
            serverURL: serverURL
        )
    }

    func callREATool(_ name: String, arguments: Data, serverURL: String) async throws -> Data {
        guard name.range(of: "^[A-Za-z0-9_.-]{1,128}$", options: .regularExpression) != nil else {
            throw ChatClientError.invalidResponse
        }
        let body = try JSONSerialization.data(
            withJSONObject: ["arguments": try JSONSerialization.jsonObject(with: arguments)]
        )
        return try await authenticatedData(
            path: "/v2/reverse-engineering/tools/\\(name)/call",
            method: "POST",
            serverURL: serverURL,
            body: body
        )
    }

    func uploadREAIPA(fileURL: URL, serverURL: String) async throws -> Data {
        let credentials = try await registerInstallationIfNeeded(serverURL: serverURL)
        guard let url = endpoint("/v2/reverse-engineering/ipa/upload", serverURL: serverURL) else {
            throw ChatClientError.invalidServerURL
        }
        let access = fileURL.startAccessingSecurityScopedResource()
        defer { if access { fileURL.stopAccessingSecurityScopedResource() } }
        let attributes = try FileManager.default.attributesOfItem(atPath: fileURL.path)
        let size = (attributes[.size] as? NSNumber)?.intValue ?? 0
        guard size > 0, size <= 200 * 1024 * 1024,
              fileURL.pathExtension.lowercased() == "ipa" else {
            throw ChatClientError.invalidResponse
        }

        let boundary = UUID().uuidString
        let bodyURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("ultron-rea-\\(UUID().uuidString).multipart")
        FileManager.default.createFile(atPath: bodyURL.path, contents: nil)
        defer { try? FileManager.default.removeItem(at: bodyURL) }
        let output = try FileHandle(forWritingTo: bodyURL)
        let input = try FileHandle(forReadingFrom: fileURL)
        defer {
            try? input.close()
            try? output.close()
        }
        let header = "--\\(boundary)\\r\\nContent-Disposition: form-data; name=\\"file\\"; filename=\\"\\(fileURL.lastPathComponent)\\"\\r\\nContent-Type: application/octet-stream\\r\\n\\r\\n"
        try output.write(contentsOf: Data(header.utf8))
        while let chunk = try input.read(upToCount: 1024 * 1024), !chunk.isEmpty {
            try output.write(contentsOf: chunk)
        }
        try output.write(contentsOf: Data("\\r\\n--\\(boundary)--\\r\\n".utf8))
        try output.close()

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 300
        request.setValue(credentials.id, forHTTPHeaderField: "X-Installation-ID")
        request.setValue(credentials.token, forHTTPHeaderField: "X-Installation-Token")
        request.setValue("multipart/form-data; boundary=\\(boundary)", forHTTPHeaderField: "Content-Type")
        let (data, response) = try await URLSession.shared.upload(for: request, fromFile: bodyURL)
        guard let http = response as? HTTPURLResponse else { throw ChatClientError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else { throw ChatClientError.serverError(http.statusCode) }
        return data
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
