import AVFoundation
import UIKit

/// Native actions stay user-initiated and within public iOS APIs.
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

    /// Return the first explicit HTTPS link in a message for a user-tapped SwiftUI Link.
    static func firstHTTPSURL(in text: String) -> URL? {
        guard let expression = try? NSRegularExpression(pattern: #"https://[^\\s<>()]+"#) else {
            return nil
        }
        let range = NSRange(text.startIndex..<text.endIndex, in: text)
        guard let match = expression.firstMatch(in: text, range: range),
              let matchRange = Range(match.range, in: text) else {
            return nil
        }
        let raw = String(text[matchRange]).trimmingCharacters(
            in: CharacterSet(charactersIn: ".,;:!?)]}")
        )
        guard let url = URL(string: raw),
              url.scheme?.lowercased() == "https",
              url.host != nil else {
            return nil
        }
        return url
    }
}
