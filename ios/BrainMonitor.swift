import AVFoundation
import SwiftUI
import UIKit

enum BrainPhase: Equatable {
    case idle
    case connecting
    case processing
    case responding
    case error

    var title: String {
        switch self {
        case .idle: return "Núcleo em espera"
        case .connecting: return "Conectando"
        case .processing: return "Processando"
        case .responding: return "Respondendo"
        case .error: return "Falha na conexão"
        }
    }
}

struct BrainMonitorView: View {
    let phase: BrainPhase
    @State private var pulse = false

    private var active: Bool { phase == .connecting || phase == .processing || phase == .responding }

    var body: some View {
        ZStack {
            Circle()
                .stroke(Color.cyan.opacity(0.22), lineWidth: 2)
                .frame(width: 48, height: 48)
                .scaleEffect(pulse && active ? 1.18 : 0.92)
                .opacity(pulse && active ? 0.25 : 0.8)
            Circle()
                .fill(phase == .error ? Color.red : Color.cyan.opacity(0.16))
                .frame(width: 38, height: 38)
            Image(systemName: "brain.head.profile")
                .font(.system(size: 21, weight: .semibold))
                .foregroundStyle(phase == .error ? .red : .cyan)
                .symbolEffect(.pulse, options: .repeating, isActive: active)
        }
        .frame(width: 50, height: 50)
        .onAppear {
            withAnimation(.easeInOut(duration: 0.9).repeatForever(autoreverses: true)) {
                pulse = true
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Estado do núcleo: \(phase.title)")
    }
}

enum DeviceActions {
    private static let synthesizer = AVSpeechSynthesizer()

    static func copy(_ text: String) {
        UIPasteboard.general.string = text
    }

    static func speak(_ text: String) {
        if synthesizer.isSpeaking { synthesizer.stopSpeaking(at: .immediate) }
        let utterance = AVSpeechUtterance(string: text)
        utterance.voice = AVSpeechSynthesisVoice(language: "pt-BR")
        synthesizer.speak(utterance)
    }

    static func stopSpeaking() {
        synthesizer.stopSpeaking(at: .immediate)
    }

    static func firstHTTPSURL(in text: String) -> URL? {
        for token in text.split(whereSeparator: { $0.isWhitespace }) {
            let cleaned = token.trimmingCharacters(in: CharacterSet(charactersIn: ".,;:!?()[]{}<>\"'"))
            guard let url = URL(string: cleaned),
                  url.scheme?.lowercased() == "https",
                  url.host != nil else { continue }
            return url
        }
        return nil
    }
}
