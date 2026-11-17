import SwiftUI

enum BrainPhase: Equatable {
    case idle
    case connecting
    case processing
    case responding
    case error

    var title: String {
        switch self {
        case .idle: return "Núcleo em espera"
        case .connecting: return "Conectando ao núcleo"
        case .processing: return "Processando solicitação"
        case .responding: return "Resposta recebida"
        case .error: return "Falha na conexão"
        }
    }

    var intensity: Double {
        switch self {
        case .idle: return 0.32
        case .connecting: return 0.58
        case .processing: return 1.0
        case .responding: return 1.35
        case .error: return 0.12
        }
    }
}

/// Lightweight procedural hologram. Animation is driven by TimelineView,
/// not by a published timer that would invalidate the whole chat hierarchy.
struct BrainMonitorView: View {
    let phase: BrainPhase

    var body: some View {
        TimelineView(.animation(minimumInterval: phase == .idle ? 1.0 / 12.0 : 1.0 / 24.0)) { timeline in
            Canvas(opaque: false, colorMode: .linear) { context, size in
                let time = timeline.date.timeIntervalSinceReferenceDate
                let center = CGPoint(x: size.width / 2, y: size.height / 2)
                let radius = min(size.width, size.height) * 0.39
                let speed = phase.intensity
                let accent: Color = phase == .error
                    ? .red
                    : Color(red: 0.12, green: 0.72, blue: 1.0)

                // Concentric holographic rings.
                for ring in 0..<3 {
                    let ringRadius = radius * CGFloat(0.62 + Double(ring) * 0.19)
                    let rect = CGRect(
                        x: center.x - ringRadius,
                        y: center.y - ringRadius,
                        width: ringRadius * 2,
                        height: ringRadius * 2
                    )
                    var ringPath = Path()
                    ringPath.addEllipse(in: rect)
                    context.stroke(
                        ringPath,
                        with: .color(accent.opacity(0.18 + Double(ring) * 0.07)),
                        lineWidth: ring == 1 ? 1.1 : 0.7
                    )
                }

                // A small, deterministic particle network keeps CPU use bounded.
                let particleCount = 28
                var points: [CGPoint] = []
                points.reserveCapacity(particleCount)
                for index in 0..<particleCount {
                    let fraction = Double(index) / Double(particleCount)
                    let angle = fraction * .pi * 2 + time * (0.16 + speed * 0.42)
                    let wobble = 0.82 + 0.12 * sin(time * 1.4 + Double(index) * 1.7)
                    let radial = radius * CGFloat(wobble)
                    points.append(CGPoint(
                        x: center.x + CGFloat(cos(angle)) * radial,
                        y: center.y + CGFloat(sin(angle)) * radial
                    ))
                }

                var mesh = Path()
                for index in points.indices {
                    let next = points[(index + 1) % points.count]
                    mesh.move(to: points[index])
                    mesh.addLine(to: next)
                    if index.isMultiple(of: 4) {
                        mesh.move(to: center)
                        mesh.addLine(to: points[index])
                    }
                }
                context.stroke(mesh, with: .color(accent.opacity(0.32)), lineWidth: 0.65)

                // Angular core and moving energy pulse.
                let pulse = 0.82 + 0.18 * sin(time * (1.8 + speed))
                var core = Path()
                for vertex in 0..<6 {
                    let angle = Double(vertex) * .pi / 3 + time * 0.12 * speed
                    let point = CGPoint(
                        x: center.x + CGFloat(cos(angle)) * radius * 0.34 * CGFloat(pulse),
                        y: center.y + CGFloat(sin(angle)) * radius * 0.34 * CGFloat(pulse)
                    )
                    if vertex == 0 { core.move(to: point) } else { core.addLine(to: point) }
                }
                core.closeSubpath()
                context.stroke(core, with: .color(accent.opacity(0.9)), lineWidth: 1.25)

                let coreRect = CGRect(x: center.x - 3.5, y: center.y - 3.5, width: 7, height: 7)
                context.fill(Path(ellipseIn: coreRect), with: .color(.white.opacity(0.95)))

                for (index, point) in points.enumerated() {
                    let size: CGFloat = index.isMultiple(of: 3) ? 3.0 : 1.8
                    let dot = CGRect(x: point.x - size / 2, y: point.y - size / 2, width: size, height: size)
                    context.fill(Path(ellipseIn: dot), with: .color(accent.opacity(0.55 + 0.35 * pulse)))
                }
            }
        }
        .frame(width: 72, height: 72)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Monitor holográfico do ULTRON: \(phase.title)")
    }
}
