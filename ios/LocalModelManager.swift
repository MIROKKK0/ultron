import Foundation
import CryptoKit
import SwiftLlama

@MainActor
final class LocalModelManager: ObservableObject {
    @Published private(set) var isModelAvailable = false
    @Published private(set) var isDownloading = false
    @Published var errorMessage: String?

    private let filename = "Qwen3-0.6B-Q4_K_M.gguf"
    private let expectedBytes: Int64 = 484_220_288
    private let expectedSHA256 = "373db06783953f0981572d008f183eb2167b93304f5adbf7c4ce6ed6a91ee437"
    private let downloadURL = URL(string: "https://huggingface.co/tauqir02/Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q4_K_M.gguf?download=true")!
    private var service: LlamaService?

    private var modelFileURL: URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent(filename)
    }

    init() {
        refreshAvailability()
    }

    func refreshAvailability() {
        let attributes = try? FileManager.default.attributesOfItem(atPath: modelFileURL.path)
        let size = (attributes?[.size] as? NSNumber)?.int64Value ?? 0
        isModelAvailable = size == expectedBytes
    }

    func downloadModel() async {
        guard !isDownloading else { return }
        isDownloading = true
        errorMessage = nil
        defer { isDownloading = false }

        do {
            var request = URLRequest(url: downloadURL)
            request.timeoutInterval = 600
            request.setValue("application/octet-stream", forHTTPHeaderField: "Accept")
            let (temporaryURL, response) = try await URLSession.shared.download(for: request)
            guard let http = response as? HTTPURLResponse,
                  (200...299).contains(http.statusCode) else {
                throw LocalModelError.downloadFailed
            }

            let attributes = try FileManager.default.attributesOfItem(atPath: temporaryURL.path)
            let size = (attributes[.size] as? NSNumber)?.int64Value ?? 0
            guard size == expectedBytes else { throw LocalModelError.invalidSize }

            let digest = try Self.sha256(of: temporaryURL)
            guard digest == expectedSHA256 else { throw LocalModelError.checksumMismatch }

            if FileManager.default.fileExists(atPath: modelFileURL.path) {
                try FileManager.default.removeItem(at: modelFileURL)
            }
            try FileManager.default.moveItem(at: temporaryURL, to: modelFileURL)
            refreshAvailability()
            guard isModelAvailable else { throw LocalModelError.invalidSize }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func removeModel() {
        do {
            await service?.stopCompletion()
            service = nil
            if FileManager.default.fileExists(atPath: modelFileURL.path) {
                try FileManager.default.removeItem(at: modelFileURL)
            }
            isModelAvailable = false
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func generate(
        userMessage: String,
        previousMessages: [ChatMessage],
        brainContext: BrainContext?,
        serverReply: String
    ) async throws -> String {
        refreshAvailability()
        guard isModelAvailable else { throw LocalModelError.modelMissing }

        if service == nil {
            service = LlamaService(
                modelUrl: modelFileURL,
                config: LlamaConfig(
                    batchSize: 128,
                    maxTokenCount: 1024,
                    useGPU: true,
                    microBatchSize: 32,
                    nThreads: 2,
                    nThreadsBatch: 2
                )
            )
        }

        let roleScores = brainContext?.roleScores
            .map { "\($0.key)=\(String(format: "%.3f", $0.value))" }
            .sorted()
            .joined(separator: ", ") ?? "indisponível"
        let groupActivity = brainContext?.groupActivity
            .map { "\($0.key)=\(String(format: "%.3f", $0.value))" }
            .sorted()
            .joined(separator: ", ") ?? "indisponível"
        let connectome = brainContext?.isFullConnectome == true
            ? "conectoma FlyWire completo ativo"
            : "microcircuito LIF local; conectoma completo não carregado"

        let systemPrompt = """
        Você é o módulo de linguagem local do ULTRON. O núcleo central obrigatório é o FlyBrain, que já processou a mensagem no servidor antes desta geração. Você não substitui, ignora nem simula o FlyBrain. Use os sinais abaixo como controle de prioridade, não como fatos sobre o mundo.
        Estado neural: \(brainContext?.core ?? "FlyBrain") / \(brainContext?.runtime ?? "runtime local").
        Estado do conectoma: \(connectome).
        Novidade: \(brainContext?.novelty ?? 0).
        Atividade dos grupos: \(groupActivity).
        Prioridades neurais: \(roleScores).
        Resposta e contexto verificados pelo servidor: \(serverReply)
        Responda em português brasileiro natural, direto e útil. Preserve URLs e fatos do contexto do servidor. Não invente fontes, resultados de pesquisa, execução de ações, memória ou capacidades. Se o contexto não contiver a resposta, diga o que falta. Não afirme consciência, AGI ou autoevolução geral. Mantenha comandos matemáticos exatos e não contradiga o resultado do servidor.
        """

        var conversation: [LlamaChatMessage] = [
            LlamaChatMessage(role: .system, content: systemPrompt)
        ]
        for item in previousMessages.suffix(8) {
            let role: LlamaChatMessage.Role = item.role == .user ? .user : .assistant
            conversation.append(LlamaChatMessage(role: role, content: item.text))
        }
        conversation.append(LlamaChatMessage(role: .user, content: userMessage))

        guard let service else { throw LocalModelError.modelMissing }
        let output = try await service.respond(
            to: conversation,
            samplingConfig: LlamaSamplingConfig(temperature: 0.55, seed: UInt32.random(in: 1...UInt32.max), topP: 0.9)
        )
        let cleaned = output
            .replacingOccurrences(of: "<think>[\\s\\S]*?</think>", with: "", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines)
        guard !cleaned.isEmpty else { throw LocalModelError.emptyResponse }
        return cleaned
    }

    private static func sha256(of url: URL) throws -> String {
        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }
        var hasher = SHA256()
        while true {
            let chunk = try handle.read(upToCount: 1_048_576) ?? Data()
            if chunk.isEmpty { break }
            hasher.update(data: chunk)
        }
        return hasher.finalize().map { String(format: "%02x", $0) }.joined()
    }
}

private enum LocalModelError: LocalizedError {
    case downloadFailed
    case invalidSize
    case checksumMismatch
    case modelMissing
    case emptyResponse

    var errorDescription: String? {
        switch self {
        case .downloadFailed: return "Não foi possível baixar o modelo local."
        case .invalidSize: return "O arquivo do modelo está incompleto ou tem tamanho inesperado."
        case .checksumMismatch: return "A verificação SHA-256 do modelo falhou; o arquivo foi rejeitado."
        case .modelMissing: return "Baixe o modelo local antes de gerar respostas no iPhone."
        case .emptyResponse: return "O modelo local não produziu uma resposta válida."
        }
    }
}
