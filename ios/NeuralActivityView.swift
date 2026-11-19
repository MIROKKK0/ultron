import SwiftUI

/// A lightweight neural activity display driven by the real chat phase.
/// It visualizes activity; it does not claim to expose hidden model thoughts.
struct NeuralActivityView: View {
    let phase: BrainPhase

    private var activity: Double {
        switch phase {
        case .idle: return 0.18
        case .connecting: return 0.42
        case .processing: return 1.0
        case .responding: return 0.72
        case .error: return 0.06
        }
    }

    private var accent: Color {
        phase == .error
            ? Color(red: 1.0, green: 0.24, blue: 0.30)
            : Color(red: 0.18, green: 0.82, blue: 1.0)
    }

    var body: some View {
        TimelineView(.animation(minimumInterval: phase == .idle ? 1.0 / 12.0 : 1.0 / 30.0)) { timeline in
            Canvas(opaque: false, colorMode: .linear) { context, size in
                let time = timeline.date.timeIntervalSinceReferenceDate
                let center = CGPoint(x: size.width / 2, y: size.height / 2)
                let radius = min(size.width, size.height) * 0.39
                let count = 18
                var nodes: [CGPoint] = []
                nodes.reserveCapacity(count)

                for index in 0..<count {
                    let angle = (Double(index) / Double(count)) * .pi * 2
                    let wave = sin(time * (1.2 + activity * 3.2) - Double(index) * 0.72)
                    let radial = radius * (0.72 + 0.12 * wave)
                    nodes.append(CGPoint(
                        x: center.x + CGFloat(cos(angle + time * 0.08)) * radial,
                        y: center.y + CGFloat(sin(angle + time * 0.08)) * radial
                    ))
                }

                // Outer rings establish the holographic core.
                for ring in 0..<3 {
                    let r = radius * CGFloat(0.60 + Double(ring) * 0.22)
                    let rect = CGRect(x: center.x - r, y: center.y - r, width: r * 2, height: r * 2)
                    var ringPath = Path()
                    ringPath.addEllipse(in: rect)
                    context.stroke(ringPath, with: .color(accent.opacity(0.12 + activity * 0.10)), lineWidth: 0.7)
                }

                // Axons connect nearby neurons. A moving pulse travels along each connection.
                for index in 0..<count {
                    let links = [(index + 1) % count, (index + 5) % count]
                    for (linkIndex, target) in links.enumerated() {
                        let start = nodes[index]
                        let end = nodes[target]
                        var axon = Path()
                        axon.move(to: start)
                        axon.addLine(to: end)
                        context.stroke(axon, with: .color(accent.opacity(0.22 + activity * 0.18)), lineWidth: 0.75)

                        let progress = (time * (0.18 + activity * 1.55) + Double(index) * 0.173 + Double(linkIndex) * 0.31)
                            .truncatingRemainder(dividingBy: 1.0)
                        let pulse = CGPoint(
                            x: start.x + (end.x - start.x) * CGFloat(progress),
                            y: start.y + (end.y - start.y) * CGFloat(progress)
                        )
                        let pulseSize: CGFloat = phase == .processing ? 3.2 : 2.2
                        let pulseRect = CGRect(
                            x: pulse.x - pulseSize / 2,
                            y: pulse.y - pulseSize / 2,
                            width: pulseSize,
                            height: pulseSize
                        )
                        context.fill(Path(ellipseIn: pulseRect), with: .color(.white.opacity(0.35 + activity * 0.60)))
                    }
                }

                // Neuron bodies brighten as the agent moves through its processing phases.
                for (index, point) in nodes.enumerated() {
                    let flicker = 0.5 + 0.5 * sin(time * (2.0 + activity * 5.0) + Double(index) * 1.9)
                    let diameter: CGFloat = 2.2 + CGFloat(flicker * activity * 2.1)
                    let rect = CGRect(x: point.x - diameter / 2, y: point.y - diameter / 2,
                                      width: diameter, height: diameter)
                    context.fill(Path(ellipseIn: rect), with: .color(accent.opacity(0.45 + flicker * 0.5)))
                }

                // Central reactor pulse.
                let pulse = 0.82 + 0.18 * sin(time * (1.6 + activity * 5.0))
                let coreRadius = radius * 0.25 * CGFloat(pulse)
                let coreRect = CGRect(x: center.x - coreRadius, y: center.y - coreRadius,
                                      width: coreRadius * 2, height: coreRadius * 2)
                context.fill(Path(ellipseIn: coreRect), with: .color(accent.opacity(0.10 + activity * 0.20)))
                context.stroke(Path(ellipseIn: coreRect), with: .color(accent.opacity(0.95)), lineWidth: 1.2)

                let centerRect = CGRect(x: center.x - 3, y: center.y - 3, width: 6, height: 6)
                context.fill(Path(ellipseIn: centerRect), with: .color(.white.opacity(0.96)))
            }
        }
        .frame(width: 76, height: 76)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Núcleo neural do ULTRON: \(phase.title)")
    }
}
