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
}
