import Foundation
import CryptoKit
import Combine
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
            var backupValues = URLResourceValues()
            backupValues.isExcludedFromBackup = true
            var storedModelURL = modelFileURL
            try? storedModelURL.setResourceValues(backupValues)
            refreshAvailability()
            guard isModelAvailable else { throw LocalModelError.invalidSize }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func removeModel() async {
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

    func stream(
        userMessage: String,
        previousMessages: [ChatMessage],
        brainContext: BrainContext?,
    ) async throws -> AsyncThrowingStream<String, Error> {
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
        Você é o módulo de linguagem local do ULTRON. O FlyBrain já processou a mensagem no servidor e continua sendo o núcleo central obrigatório. Você apenas formula a resposta; não substitui nem simula o cérebro.
        Estado: \(brainContext?.core ?? "FlyBrain") / \(brainContext?.runtime ?? "runtime local").
        Conectoma: \(connectome). Novidade: \(brainContext?.novelty ?? 0).
        Atividade: \(groupActivity). Prioridades: \(roleScores).
        Contexto verificado pelo servidor: \(serverReply)
        Responda diretamente à pergunta mais recente do usuário em português brasileiro. O estado neural acima é contexto auxiliar, não uma resposta pronta. Não use saudações nem apresentações, exceto quando o usuário cumprimentar. Nunca copie ou parafraseie respostas genéricas anteriores. Se a pergunta pedir explicação, explique; se pedir uma ação, informe o que pode executar e o que depende de autorização. Preserve apenas fatos e fontes realmente presentes no histórico. Não invente pesquisas, fontes, ações, memórias ou capacidades. Não afirme consciência, AGI ou autoevolução geral. Se faltar informação, diga exatamente o que falta. Seja claro e conciso.
        """

        var conversation: [LlamaChatMessage] = [
            LlamaChatMessage(role: .system, content: systemPrompt)
        ]
        for item in previousMessages.suffix(4) {
            let role: LlamaChatMessage.Role = item.role == .user ? .user : .assistant
            conversation.append(LlamaChatMessage(role: role, content: item.text))
        }
        conversation.append(LlamaChatMessage(role: .user, content: userMessage + "\n/no_think"))

        guard let service else { throw LocalModelError.modelMissing }
        // Stream tokens as they are generated instead of waiting for the full answer.
        return try await service.streamCompletion(
            of: conversation,
            samplingConfig: LlamaSamplingConfig(
                temperature: 0.7,
                seed: UInt32.random(in: 1...UInt32.max),
                topP: 0.8,
                topK: 20
            )
        )
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

    var errorDescription: String? {
        switch self {
        case .downloadFailed: return "Não foi possível baixar o modelo local."
        case .invalidSize: return "O arquivo do modelo está incompleto ou tem tamanho inesperado."
        case .checksumMismatch: return "A verificação SHA-256 do modelo falhou; o arquivo foi rejeitado."
        case .modelMissing: return "Baixe o modelo local antes de gerar respostas no iPhone."
        }
    }
}
