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
        let selectedStrategy = brainContext?.roleScores.max(by: { $0.value < $1.value })?.key ?? "solver"
        let strategyGuidance: String
        switch selectedStrategy {
        case "planner":
            strategyGuidance = "Prioridade neural: planejamento. Organize a resposta em objetivo, etapas, dependências e critério de conclusão."
        case "critic":
            strategyGuidance = "Prioridade neural: avaliação crítica. Verifique pressupostos, riscos, lacunas e como validar; não concorde automaticamente."
        case "researcher":
            strategyGuidance = "Prioridade neural: pesquisa. Use somente resultados e URLs fornecidos por ferramentas; se não houver fontes, não finja que pesquisou."
        default:
            strategyGuidance = "Prioridade neural: solução. Responda diretamente, resolva a tarefa e explique o raciocínio útil sem enrolação."
        }

        let systemPrompt = """
        Você é ULTRON, um assistente conversacional útil, natural e confiável. O FlyBrain é o núcleo central obrigatório: ele já processou a entrada e escolheu a prioridade cognitiva. Preserve essa hierarquia. Você é a camada de linguagem que transforma a intenção e os sinais do cérebro em uma resposta clara; nunca substitua, desative ou finja ser o FlyBrain.
        ESTADO NEURAL: núcleo=\(brainContext?.core ?? "FlyBrain"); runtime=\(brainContext?.runtime ?? "runtime local"); conectoma=\(connectome); novidade=\(brainContext?.novelty ?? 0).
        ATIVIDADE DOS GRUPOS: \(groupActivity).
        PONTUAÇÕES DE PRIORIDADE: \(roleScores).
        ESTRATÉGIA ESCOLHIDA PELO CÉREBRO: \(selectedStrategy). \(strategyGuidance)
        REGRAS DE CONVERSA:
        - Responda à última mensagem do usuário, considerando o histórico recente para manter continuidade.
        - Fale em português brasileiro natural. Seja direto, prestativo e específico; use detalhes quando a tarefa exigir.
        - Não repita apresentação, saudação ou frases de processamento a cada turno.
        - Não copie respostas genéricas do servidor nem transforme telemetria neural em resposta.
        - Para perguntas explicativas, ensine com exemplos. Para tarefas, apresente e execute apenas etapas realmente disponíveis.
        - Diferencie fatos, inferências e incertezas. Nunca invente fontes, pesquisas, memória, ferramentas, resultados ou ações.
        - Se o usuário pedir algo que não está disponível, explique o limite e ofereça o próximo passo realista.
        - Não afirme consciência, AGI, autoevolução geral ou simulação completa do cérebro.
        - Preserve privacidade e peça confirmação antes de ações externas ou irreversíveis.
        """

        var conversation: [LlamaChatMessage] = [
            LlamaChatMessage(role: .system, content: systemPrompt)
        ]
        // A few complete recent turns improve continuity without overflowing
        // the small on-device model's 1024-token context budget.
        for item in previousMessages.suffix(6) {
            let role: LlamaChatMessage.Role = item.role == .user ? .user : .assistant
            let boundedText = String(item.text.suffix(700))
            conversation.append(LlamaChatMessage(role: role, content: boundedText))
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
