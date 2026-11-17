import AppIntents
import Foundation

/// User-invoked Siri / Shortcuts action; never triggered by a remote instruction.
struct AskUltronIntent: AppIntent {
    static var title: LocalizedStringResource = "Perguntar ao ULTRON"
    static var description = IntentDescription(
        "Envia uma pergunta ao servidor configurado do ULTRON e devolve a resposta."
    )
    static var openAppWhenRun = false

    @Parameter(title: "Mensagem")
    var message: String

    func perform() async throws -> some IntentResult & ReturnsValue<String> {
        let configuredURL = UserDefaults.standard.string(forKey: "ultronServerURL")
            ?? "https://ultron-api-c5ae.onrender.com"
        let result = try await ChatClient().send(message, serverURL: configuredURL)
        return .result(value: result.reply)
    }
}

struct UltronShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: AskUltronIntent(),
            phrases: [
                "Perguntar ao \(.applicationName)",
                "Falar com \(.applicationName)"
            ],
            shortTitle: "Perguntar",
            systemImageName: "brain.head.profile"
        )
    }
}
