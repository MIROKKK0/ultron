import SwiftUI
import SceneKit
import UIKit

struct NeuralMemoryNode: Identifiable, Codable, Hashable {
    let id: String
    let content: String
    let kind: String
    let importance: Int
}

struct NeuralMemoryEdge: Identifiable, Codable, Hashable {
    var id: String { "\(sourceID)-\(targetID)-\(relation)" }
    let sourceID: String
    let targetID: String
    let relation: String
}

struct NeuralUniverseView: View {
    let nodes: [NeuralMemoryNode]
    let edges: [NeuralMemoryEdge]
    @State private var selectedNode: NeuralMemoryNode?

    var body: some View {
        ZStack(alignment: .bottom) {
            NeuralSceneView(nodes: nodes, edges: edges, selectedID: selectedNode?.id) { node in
                selectedNode = node
            }
            .ignoresSafeArea(edges: .bottom)

            VStack(spacing: 10) {
                HStack {
                    Label("UNIVERSO NEURAL", systemImage: "brain.head.profile")
                        .font(.headline.weight(.bold))
                    Spacer()
                    Text("\(nodes.count) nós · \(edges.count) conexões")
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
                .padding(12)
                .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 14))

                if let selectedNode {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(selectedNode.kind.uppercased())
                            .font(.caption.bold())
                            .foregroundStyle(.cyan)
                        Text(selectedNode.content)
                            .font(.body)
                            .lineLimit(4)
                        HStack {
                            Text("Importância: \(selectedNode.importance)/5")
                            Spacer()
                            Button("Fechar") { self.selectedNode = nil }
                        }
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    }
                    .padding(14)
                    .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16))
                } else {
                    Text("Arraste para girar · pinça para aproximar · toque em um nó")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .padding(10)
                        .background(.ultraThinMaterial, in: Capsule())
                }
            }
            .padding()
        }
        .preferredColorScheme(.dark)
    }
}

private struct NeuralSceneView: UIViewRepresentable {
    let nodes: [NeuralMemoryNode]
    let edges: [NeuralMemoryEdge]
    let selectedID: String?
    let onSelect: (NeuralMemoryNode) -> Void

    func makeCoordinator() -> Coordinator { Coordinator(onSelect: onSelect, nodes: nodes) }

    func makeUIView(context: Context) -> SCNView {
        let view = SCNView()
        view.scene = makeScene()
        view.backgroundColor = UIColor(red: 0.015, green: 0.02, blue: 0.055, alpha: 1)
        view.allowsCameraControl = true
        view.autoenablesDefaultLighting = true
        view.antialiasingMode = .multisampling4X
        let tap = UITapGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.handleTap(_:)))
        view.addGestureRecognizer(tap)
        context.coordinator.sceneView = view
        return view
    }

    func updateUIView(_ view: SCNView, context: Context) {
        context.coordinator.nodes = nodes
        view.scene = makeScene()
    }

    private func makeScene() -> SCNScene {
        let scene = SCNScene()
        let root = scene.rootNode
        let count = max(nodes.count, 1)
        var positions: [String: SCNVector3] = [:]

        for (index, memory) in nodes.enumerated() {
            let angle = Float(index) * 2.399963
            let radius = 2.0 + Float(index % 4) * 0.42
            let y = Float((index % 5) - 2) * 0.38
            let position = SCNVector3(cos(angle) * radius, y, sin(angle) * radius)
            positions[memory.id] = position

            let sphere = SCNSphere(radius: 0.10 + CGFloat(max(1, memory.importance)) * 0.025)
            let material = SCNMaterial()
            material.diffuse.contents = memory.id == selectedID ? UIColor.systemYellow : UIColor.systemRed
            material.emission.contents = UIColor.systemRed.withAlphaComponent(0.65)
            sphere.materials = [material]
            let node = SCNNode(geometry: sphere)
            node.position = position
            node.name = memory.id
            root.addChildNode(node)
        }

        for edge in edges {
            guard let start = positions[edge.sourceID], let end = positions[edge.targetID] else { continue }
            let vector = SCNVector3(end.x - start.x, end.y - start.y, end.z - start.z)
            let length = CGFloat(sqrt(vector.x * vector.x + vector.y * vector.y + vector.z * vector.z))
            let cylinder = SCNCylinder(radius: 0.008, height: length)
            cylinder.firstMaterial?.diffuse.contents = UIColor.systemTeal.withAlphaComponent(0.45)
            let line = SCNNode(geometry: cylinder)
            line.position = SCNVector3((start.x + end.x) / 2, (start.y + end.y) / 2, (start.z + end.z) / 2)
            line.look(at: end, up: root.worldUp, localFront: SCNVector3(0, 1, 0))
            root.addChildNode(line)
        }

        let camera = SCNCamera()
        let cameraNode = SCNNode()
        cameraNode.camera = camera
        cameraNode.position = SCNVector3(0, 0, max(8, Float(count) * 0.18))
        root.addChildNode(cameraNode)
        return scene
    }

    final class Coordinator: NSObject {
        weak var sceneView: SCNView?
        var nodes: [NeuralMemoryNode]
        let onSelect: (NeuralMemoryNode) -> Void
        init(onSelect: @escaping (NeuralMemoryNode) -> Void, nodes: [NeuralMemoryNode]) {
            self.onSelect = onSelect
            self.nodes = nodes
        }
        @objc func handleTap(_ gesture: UITapGestureRecognizer) {
            guard let view = sceneView else { return }
            let point = gesture.location(in: view)
            guard let hit = view.hitTest(point).first, let id = hit.node.name,
                  let memory = nodes.first(where: { $0.id == id }) else { return }
            onSelect(memory)
        }
    }
}
