import AVFoundation
import UIKit

/// Native actions deliberately stay user-initiated and inside iOS permissions.
enum DeviceActions {
    private static let speech = AVSpeechSynthesizer()

    static func copy(_ text: String) {
        UIPasteboard.general.string = text
    }

    static func speak(_ text: String) {
        if speech.isSpeaking { speech.stopSpeaking(at: .immediate) }
        let utterance = AVSpeechUtterance(string: String(text.prefix(6000)))
        utterance.voice = AVSpeechSynthesisVoice(language: "pt-BR")
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate
        speech.speak(utterance)
    }

    static func stopSpeaking() {
        speech.stopSpeaking(at: .immediate)
    }

    /// Opens only HTTPS links after an explicit tap; never executes shell commands.
    static func webURL(_ raw: String) -> URL? {
        guard let url = URL(string: raw),
              url.scheme?.lowercased() == "https",
              url.host != nil else { return nil }
        return url
    }
}
